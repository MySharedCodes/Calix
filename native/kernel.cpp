#include <boost/math/quadrature/gauss_kronrod.hpp>
#include <boost/math/tools/roots.hpp>
#include <boost/math/tools/minima.hpp>
#include <boost/math/special_functions/ellint_1.hpp>
#include <boost/math/special_functions/ellint_2.hpp>
#include <boost/numeric/odeint.hpp>
#include <array>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <vector>
#include "cpu.h"

#ifdef _WIN32
#define CALIX_API extern "C" __declspec(dllexport)
#else
#define CALIX_API extern "C" __attribute__((visibility("default")))
#endif

namespace {
double evaluate(const int32_t* ops, const double* args, int n, double x, double y, double z,
                const double* variables = nullptr, int variable_count = 0) {
    std::array<double, 512> stack;
    int top = 0;
    for (int i = 0; i < n; ++i) {
        const int op = ops[i];
        if (op >= 100) {
            if (!variables || op - 100 >= variable_count || top >= 512) throw std::runtime_error("Invalid state operand");
            stack[top++] = variables[op - 100];
        } else if (op < 10) {
            if (top >= 512) throw std::runtime_error("Expression stack overflow");
            switch (op) {
            case 0: stack[top++] = args[i]; break;
            case 1: stack[top++] = x; break;
            case 2: stack[top++] = y; break;
            case 3: stack[top++] = z; break;
            default: throw std::runtime_error("Unknown operand");
            }
        } else if (op >= 10 && op <= 14) {
            if (top < 2) throw std::runtime_error("Invalid expression");
            const double b = stack[--top];
            double& a = stack[top - 1];
            switch (op) {
            case 10: a += b; break;
            case 11: a -= b; break;
            case 12: a *= b; break;
            case 13: a /= b; break;
            case 14: a = std::pow(a, b); break;
            }
        } else {
            if (top < 1) throw std::runtime_error("Invalid expression");
            double& a = stack[top - 1];
            switch (op) {
            case 15: a = -a; break;
            case 20: a = std::sin(a); break;
            case 21: a = std::cos(a); break;
            case 22: a = std::tan(a); break;
            case 23: a = std::exp(a); break;
            case 24: a = std::log(a); break;
            case 25: a = std::sqrt(a); break;
            case 26: a = std::abs(a); break;
            case 27: a = std::asin(a); break;
            case 28: a = std::acos(a); break;
            case 29: a = std::atan(a); break;
            case 30: a = std::sinh(a); break;
            case 31: a = std::cosh(a); break;
            case 32: a = std::tanh(a); break;
            case 33: a = std::erf(a); break;
            case 34: a = std::tgamma(a); break;
            case 35: a = std::floor(a); break;
            case 36: a = std::ceil(a); break;
            case 37: a = boost::math::ellint_1(std::sqrt(a)); break;
            case 38: a = boost::math::ellint_2(std::sqrt(a)); break;
            default: throw std::runtime_error("Unknown instruction");
            }
        }
    }
    if (top != 1) throw std::runtime_error("Invalid result stack");
    return stack[0];
}
}

CALIX_API int calix_abi_version() { return 1; }

namespace {
std::array<double, 3> projectile(double coefficient, double mass, double speed,
                                  double gravity, int model, double angle) {
    const double pi = std::acos(-1.0);
    if (angle <= 0 || angle >= pi/2) return {0, angle, 0};
    if (coefficient == 0) return {speed*speed/gravity*std::sin(2*angle), angle, 2*speed/gravity*std::sin(angle)};
    using namespace boost::numeric::odeint;
    using state_type = std::array<double, 4>;
    const double q = coefficient/mass*(model == 1 ? speed/gravity : speed*speed/gravity);
    auto stepper = make_dense_output(2e-11, 2e-11, runge_kutta_dopri5<state_type>());
    state_type state{0, 0, std::cos(angle), std::sin(angle)};
    auto system = [&](const state_type& u, state_type& du, double) {
        const double drag = q*(model == 1 ? 1 : std::hypot(u[2],u[3]));
        du = {u[2],u[3],-drag*u[2],-1-drag*u[3]};
    };
    stepper.initialize(state, 0, std::min({0.001,0.01/(1+q),0.1*std::sin(angle)}));
    for (int steps = 0; steps < 200000; ++steps) {
        const double previous = stepper.current_time();
        stepper.do_step(system);
        if (!std::isfinite(stepper.current_state()[1])) throw std::runtime_error("Nonfinite projectile state");
        if (stepper.current_state()[1] <= 0) {
            if (previous == 0) throw std::runtime_error("Projectile launch too close to ground event");
            auto height = [&](double t) { stepper.calc_state(t,state); return state[1]; };
            boost::uintmax_t iterations = 100;
            auto interval = boost::math::tools::toms748_solve(height, previous, stepper.current_time(),
                boost::math::tools::eps_tolerance<double>(42), iterations);
            const double landing = (interval.first+interval.second)/2;
            stepper.calc_state(landing,state);
            return {state[0]*speed*speed/gravity, angle, landing*speed/gravity};
        }
    }
    throw std::runtime_error("Projectile step limit");
}
}

CALIX_API int calix_projectile(double coefficient, double mass, double speed, double gravity,
                               int model, double angle, int optimize, double* result) {
    if (!result || !std::isfinite(coefficient) || coefficient < 0 || !std::isfinite(mass) || mass <= 0 ||
        !std::isfinite(speed) || speed <= 0 || !std::isfinite(gravity) || gravity <= 0 ||
        !std::isfinite(angle) || angle < 0 || angle > std::acos(-1.0)/2 || (model != 1 && model != 2)) return -1;
    try {
        if (optimize) {
            // A global angle scan brackets the best interior maximum before Brent refinement.
            const double step = std::acos(-1.0)/128;
            int best = 1; double maximum = -1;
            for (int i=1;i<64;++i) {
                const double range = projectile(coefficient,mass,speed,gravity,model,i*step)[0];
                if (range > maximum) { maximum=range;best=i; }
            }
            boost::uintmax_t iterations=100;
            auto optimum = boost::math::tools::brent_find_minima([&](double theta) {
                return -projectile(coefficient,mass,speed,gravity,model,theta)[0];
            }, (best-1)*step, (best+1)*step, 40, iterations);
            if (iterations>=100) return -3;
            angle=optimum.first;
        }
        const auto flight=projectile(coefficient,mass,speed,gravity,model,angle);
        std::copy(flight.begin(),flight.end(),result);
        return 0;
    } catch (...) { return -2; }
}

CALIX_API int calix_callback_root(double (*function)(double), double lower, double upper, double* result) {
    if (!function || !result || !std::isfinite(lower) || !std::isfinite(upper) || !(lower < upper)) return -1;
    try {
        auto evaluate_function=[&](double x) { double v=function(x);if(!std::isfinite(v))throw std::runtime_error("Nonfinite callback");return v; };
        boost::uintmax_t iterations=150;
        auto bracket=boost::math::tools::toms748_solve(evaluate_function,lower,upper,boost::math::tools::eps_tolerance<double>(40),iterations);
        if(iterations>=150)return -3;
        *result=(bracket.first+bracket.second)/2;
        return 0;
    } catch (...) { return -2; }
}

CALIX_API int calix_ode_system(const int32_t* ops, const double* args, const int32_t* offsets,
                              int dimension, double start, double end, const double* initial,
                              int points, double tolerance, double* output) {
    if (!ops || !args || !offsets || !initial || !output || dimension < 1 || dimension > 32 ||
        points < 2 || points > 20000 || !std::isfinite(start) || !std::isfinite(end) || !(start < end) ||
        !std::isfinite(tolerance) || tolerance <= 0 || offsets[0] != 0) return -1;
    for (int i = 0; i < dimension; ++i) {
        if (!std::isfinite(initial[i]) || offsets[i+1] <= offsets[i] || offsets[i+1] - offsets[i] > 4096) return -1;
    }
    try {
        using namespace boost::numeric::odeint;
        using state_type = std::vector<double>;
        auto stepper = make_dense_output(tolerance, tolerance, runge_kutta_dopri5<state_type>());
        state_type state(2*dimension, 0), derivative(2*dimension), variables(dimension+1);
        std::copy(initial, initial + dimension, state.begin());
        auto system = [&](const state_type& y, state_type& dy, double t) {
            variables[0] = t;
            std::copy(y.begin(), y.begin()+dimension, variables.begin()+1);
            for (int j = 0; j < dimension; ++j) {
                dy[j] = evaluate(ops+offsets[j], args+offsets[j], offsets[j+1]-offsets[j],
                                 t, y[0], dimension > 1 ? y[1] : 0, variables.data(), dimension+1);
                dy[j+dimension] = y[j];
                if (!std::isfinite(dy[j])) throw std::runtime_error("Nonfinite ODE derivative");
            }
        };
        stepper.initialize(state, start, (end-start)/(points-1));
        unsigned long steps = 0;
        for (int i = 0; i < points; ++i) {
            const double t = start + (end-start)*i/(points-1);
            if (i) {
                while (stepper.current_time() < t) {
                    if (++steps > 1000000) throw std::runtime_error("ODE step limit");
                    stepper.do_step(system);
                }
                stepper.calc_state(t, state);
            }
            system(state, derivative, t);
            for (int j = 0; j < 2*dimension; ++j) {
                if (!std::isfinite(state[j])) return -3;
                output[i*4*dimension+j] = state[j];
                output[i*4*dimension+2*dimension+j] = derivative[j];
            }
        }
        return 0;
    } catch (...) { return -2; }
}

// Two coupled velocity components plus their displacement integrals share each adaptive step.
CALIX_API int calix_ode_pair(const int32_t* ops1, const double* args1, int n1,
                            const int32_t* ops2, const double* args2, int n2,
                            double start, double end, double v1, double v2, int points,
                            double tolerance, double* output) {
    if (!ops1 || !args1 || !ops2 || !args2 || !output || n1 < 1 || n2 < 1 || n1 > 4096 || n2 > 4096 ||
        points < 2 || points > 20000 || !std::isfinite(start) || !std::isfinite(end) || !(start < end) ||
        !std::isfinite(v1) || !std::isfinite(v2) || !std::isfinite(tolerance) || tolerance <= 0) return -1;
    try {
        using namespace boost::numeric::odeint;
        using state_type = std::array<double, 4>;
        auto stepper = make_dense_output(tolerance, tolerance, runge_kutta_dopri5<state_type>());
        state_type state{v1, v2, 0, 0};
        auto system = [&](const state_type& y, state_type& dy, double t) {
            dy[0] = evaluate(ops1, args1, n1, t, y[0], y[1]);
            dy[1] = evaluate(ops2, args2, n2, t, y[0], y[1]);
            dy[2] = y[0]; dy[3] = y[1];
            for (double value : dy) if (!std::isfinite(value)) throw std::runtime_error("Nonfinite ODE derivative");
        };
        stepper.initialize(state, start, (end - start) / (points - 1));
        unsigned long steps = 0;
        for (int i = 0; i < points; ++i) {
            double t = start + (end - start) * i / (points - 1);
            if (i) {
                while (stepper.current_time() < t) {
                    if (++steps > 1000000) throw std::runtime_error("ODE step limit");
                    stepper.do_step(system);
                }
                stepper.calc_state(t, state);
            }
            state_type derivative;
            system(state, derivative, t);
            for (int j = 0; j < 4; ++j) {
                if (!std::isfinite(state[j])) return -3;
                output[i * 8 + j] = state[j];
                output[i * 8 + j + 4] = derivative[j];
            }
        }
        return 0;
    } catch (...) { return -2; }
}

CALIX_API int calix_extremum(const int32_t* ops, const double* args, int n,
                            double lo, double hi, int maximize, double* location, double* value) {
    if (!ops || !args || !location || !value || n <= 0 || n > 4096 || !std::isfinite(lo) || !std::isfinite(hi) || !(lo < hi)) return -1;
    try {
        auto f = [&](double x) {
            const double y = evaluate(ops, args, n, x, 0, 0);
            if (!std::isfinite(y)) throw std::runtime_error("Nonfinite objective");
            return maximize ? -y : y;
        };
        boost::uintmax_t iterations = 512;
        auto best = boost::math::tools::brent_find_minima(f, lo, hi, 48, iterations);
        if (iterations >= 512) return -3;
        for (double x : {lo, hi}) { const double y = f(x); if (y < best.second) best = {x, y}; }
        *location = best.first;
        *value = maximize ? -best.second : best.second;
        return 0;
    } catch (...) { return -2; }
}

CALIX_API int calix_batch(const int32_t* ops, const double* args, int n,
                         const double* xs, const double* ys, const double* zs,
                         int count, double* output) {
    if (!ops || !args || !xs || !output || n <= 0 || n > 4096 || count < 0) return -1;
    try {
        const int done = calix_dispatch_batch(ops,args,n,xs,ys,zs,count,output);
        for (int i = done; i < count; ++i)
            output[i] = evaluate(ops, args, n, xs[i], ys ? ys[i] : 0, zs ? zs[i] : 0);
        return 0;
    } catch (...) { return -2; }
}

CALIX_API int calix_batch_variables(const int32_t* ops, const double* args, int n,
                                   const double* coordinates, int variables, int count, double* output) {
    if (!ops || !args || !coordinates || !output || n <= 0 || n > 4096 || variables < 1 || variables > 33 || count < 0) return -1;
    try {
        for (int i = 0; i < count; ++i) {
            const double* row = coordinates + i*variables;
            output[i] = evaluate(ops, args, n, row[0], variables > 1 ? row[1] : 0,
                                 variables > 2 ? row[2] : 0, row, variables);
        }
        return 0;
    } catch (...) { return -2; }
}

CALIX_API int calix_root(const int32_t* ops, const double* args, int n,
                        double lo, double hi, double tolerance, double* result) {
    if (!result || !(lo < hi) || tolerance <= 0) return -1;
    try {
        auto f = [&](double x) {
            double value = evaluate(ops, args, n, x, 0, 0);
            if (!std::isfinite(value)) throw std::runtime_error("Nonfinite root function");
            return value;
        };
        boost::uintmax_t iterations = 256;
        auto interval = boost::math::tools::toms748_solve(f, lo, hi,
            [&](double a, double b) { return std::abs(b-a) <= tolerance * (1 + std::max(std::abs(a), std::abs(b))); }, iterations);
        *result = (interval.first + interval.second) / 2;
        return std::isfinite(*result) ? 0 : -3;
    } catch (...) { return -2; }
}

CALIX_API int calix_integrate(const int32_t* ops, const double* args, int n,
                             double lo, double hi, double tolerance,
                             double* result, double* error) {
    if (!result || !error || !std::isfinite(lo) || !std::isfinite(hi) || tolerance <= 0) return -1;
    try {
        *result = boost::math::quadrature::gauss_kronrod<double, 61>::integrate(
            [&](double x) { return evaluate(ops, args, n, x, 0, 0); }, lo, hi, 12, tolerance, error);
        return std::isfinite(*result) && std::isfinite(*error) ? 0 : -3;
    } catch (...) { return -2; }
}

CALIX_API int calix_ode(const int32_t* ops, const double* args, int n,
                       double start, double end, double initial, int points,
                       double tolerance, double* times, double* values) {
    if (!times || !values || points < 2 || points > 20000 || !(start < end) || tolerance <= 0) return -1;
    try {
        using namespace boost::numeric::odeint;
        using state_type = std::array<double, 1>;
        auto stepper = make_dense_output(tolerance, tolerance, runge_kutta_dopri5<state_type>());
        state_type state{initial};
        auto system = [&](const state_type& s, state_type& ds, double t) {
            ds[0] = evaluate(ops, args, n, t, s[0], 0);
            if (!std::isfinite(ds[0])) throw std::runtime_error("Nonfinite ODE derivative");
        };
        stepper.initialize(state, start, (end - start) / (points - 1));
        unsigned long steps = 0;
        for (int i = 0; i < points; ++i) {
            const double t = start + (end-start) * i / (points-1);
            if (i == 0) { times[i] = start; values[i] = initial; continue; }
            while (stepper.current_time() < t) {
                if (++steps > 1000000) throw std::runtime_error("ODE step limit");
                stepper.do_step(system);
            }
            stepper.calc_state(t, state);
            times[i] = t;
            values[i] = state[0];
            if (!std::isfinite(state[0])) return -3;
        }
        return 0;
    } catch (...) { return -2; }
}
