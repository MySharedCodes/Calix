#include <Eigen/Dense>
#include <array>
#include <cmath>
#include <cstdint>
#include <random>
#include <vector>

#ifdef _WIN32
#define CALIX_API extern "C" __declspec(dllexport)
#else
#define CALIX_API extern "C" __attribute__((visibility("default")))
#endif

namespace {
using Matrix=Eigen::Matrix3cd;
using Complex=std::complex<double>;
struct Lattice {
    int length,volume;
    std::vector<Matrix> links;
    std::vector<std::array<int,8>> neighbors;
    explicit Lattice(int l):length(l),volume(l*l*l*l),links(volume*4,Matrix::Identity()),neighbors(volume) {
        for(int x=0;x<volume;++x) {
            int stride=1;
            for(int mu=0;mu<4;++mu) {
                int coordinate=(x/stride)%length;
                neighbors[x][2*mu]=x+(coordinate==length-1?1-length:1)*stride;
                neighbors[x][2*mu+1]=x+(coordinate==0?length-1:-1)*stride;
                stride*=length;
            }
        }
    }
    int next(int x,int mu)const{return neighbors[x][2*mu];}
    int prev(int x,int mu)const{return neighbors[x][2*mu+1];}
    const Matrix& at(int x,int mu)const{return links[4*x+mu];}
    Matrix staple(int x,int mu)const {
        Matrix result=Matrix::Zero();
        for(int nu=0;nu<4;++nu)if(nu!=mu) {
            result+=at(next(x,mu),nu)*at(next(x,nu),mu).adjoint()*at(x,nu).adjoint();
            int y=prev(x,nu);
            result+=at(next(y,mu),nu).adjoint()*at(y,mu).adjoint()*at(y,nu);
        }
        return result;
    }
    double loop(int x,int mu,int nu,int r,int t)const {
        Matrix product=Matrix::Identity();
        for(int i=0;i<r;++i){product=product*at(x,mu);x=next(x,mu);}
        for(int i=0;i<t;++i){product=product*at(x,nu);x=next(x,nu);}
        for(int i=0;i<r;++i){x=prev(x,mu);product=product*at(x,mu).adjoint();}
        for(int i=0;i<t;++i){x=prev(x,nu);product=product*at(x,nu).adjoint();}
        return product.trace().real()/3;
    }
    double wilson(int r,int t)const {
        double value=0;
        for(int x=0;x<volume;++x)for(int mu=0;mu<4;++mu)for(int nu=mu+1;nu<4;++nu) {
            value+=loop(x,mu,nu,r,t);
            if(r!=t)value+=loop(x,mu,nu,t,r);
        }
        return value/(volume*6*(r==t?1:2));
    }
    double polyakov()const {
        double value=0;
        int spatial=volume/length;
        for(int x=0;x<spatial;++x) {
            Matrix p=Matrix::Identity();int y=x;
            for(int t=0;t<length;++t){p=p*at(y,3);y=next(y,3);}
            value+=p.trace().real()/3;
        }
        return value/spatial;
    }
};
struct Random {
    std::mt19937_64 generator;
    std::uniform_real_distribution<double> uniform{0,1};
    std::normal_distribution<double> normal{0,1};
    explicit Random(uint64_t seed):generator(seed){}
    Matrix proposal(int a,int b,double step) {
        Eigen::Vector3d axis(normal(generator),normal(generator),normal(generator));
        axis.normalize();
        double angle=(2*uniform(generator)-1)*step,c=std::cos(angle),s=std::sin(angle);
        Matrix r=Matrix::Identity();
        r(a,a)=Complex(c,s*axis[2]);r(b,b)=Complex(c,-s*axis[2]);
        r(a,b)=Complex(s*axis[1],s*axis[0]);r(b,a)=Complex(-s*axis[1],s*axis[0]);
        return r;
    }
};
}

CALIX_API int calix_lattice_su3(int length,double beta,int warmup,int samples,int interval,
    double step,uint64_t seed,double* history,double* measured,double* diagnostics) {
    if(length<2 || length>6 || !std::isfinite(beta) || beta<0 || beta>100 ||
        warmup<0 || samples<2 || interval<1 || warmup+int64_t(samples)*interval>10000 ||
        !std::isfinite(step) || step<=0 || step>3.141592653589793 || !history || !measured || !diagnostics)return -1;
    try {
        Lattice lattice(length);Random random(seed);
        const int pairs[3][2]={{0,1},{0,2},{1,2}};
        int count=0,total=warmup+samples*interval;
        for(int sweep=0;sweep<total;++sweep) {
            int accepted=0;
            for(int x=0;x<lattice.volume;++x)for(int mu=0;mu<4;++mu) {
                Matrix staple=lattice.staple(x,mu);
                Matrix& link=lattice.links[4*x+mu];
                for(const auto& pair:pairs) {
                    Matrix candidate=random.proposal(pair[0],pair[1],step)*link;
                    double delta=-beta/3*((candidate-link)*staple).trace().real();
                    if(delta<=0 || std::log(random.uniform(random.generator))<-delta){link=candidate;++accepted;}
                }
            }
            double plaquette=lattice.wilson(1,1);
            history[3*sweep]=sweep+1;history[3*sweep+1]=plaquette;
            history[3*sweep+2]=double(accepted)/(lattice.volume*12);
            if(sweep>=warmup && (sweep-warmup+1)%interval==0) {
                measured[4*count]=plaquette;measured[4*count+1]=lattice.wilson(1,2);
                measured[4*count+2]=lattice.wilson(2,2);measured[4*count+3]=lattice.polyakov();++count;
            }
        }
        diagnostics[0]=0;diagnostics[1]=0;
        for(const auto& u:lattice.links) {
            diagnostics[0]=std::max(diagnostics[0],(u*u.adjoint()-Matrix::Identity()).norm());
            diagnostics[1]=std::max(diagnostics[1],std::abs(u.determinant()-Complex(1,0)));
        }
        // An independent random local gauge transformation must preserve all loops.
        std::array<double,4> before{lattice.wilson(1,1),lattice.wilson(1,2),lattice.wilson(2,2),lattice.polyakov()};
        std::vector<Matrix> gauge(lattice.volume);
        for(auto& g:gauge){g=Matrix::Identity();for(const auto& pair:pairs)g=random.proposal(pair[0],pair[1],3.0)*g;}
        for(int x=0;x<lattice.volume;++x)for(int mu=0;mu<4;++mu)
            lattice.links[4*x+mu]=gauge[x]*lattice.at(x,mu)*gauge[lattice.next(x,mu)].adjoint();
        std::array<double,4> after{lattice.wilson(1,1),lattice.wilson(1,2),lattice.wilson(2,2),lattice.polyakov()};
        diagnostics[2]=0;
        for(int i=0;i<4;++i)diagnostics[2]=std::max(diagnostics[2],std::abs(after[i]-before[i]));
        return 0;
    }catch(...){return -2;}
}

// Exposed for independent validation of the local action used by Metropolis.
CALIX_API int calix_lattice_observe(int length,const double* raw,int site,int mu,
    double* plaquette,double* staple) {
    if(length<2 || length>6 || !raw || !plaquette || !staple || mu<0 || mu>3)return -1;
    Lattice lattice(length);
    if(site<0 || site>=lattice.volume)return -1;
    for(int l=0;l<lattice.volume*4;++l)for(int i=0;i<3;++i)for(int j=0;j<3;++j) {
        int offset=(l*9+i*3+j)*2;lattice.links[l](i,j)=Complex(raw[offset],raw[offset+1]);
    }
    *plaquette=lattice.wilson(1,1);Matrix a=lattice.staple(site,mu);
    for(int i=0;i<3;++i)for(int j=0;j<3;++j){int o=(i*3+j)*2;staple[o]=a(i,j).real();staple[o+1]=a(i,j).imag();}
    return 0;
}
