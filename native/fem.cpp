#include <Eigen/Sparse>
#include <Eigen/Dense>
#include <cmath>
#include <cstdint>
#include <vector>
#include "parallel.h"
#include "sparse_runtime.h"

#ifdef _WIN32
#define CALIX_API extern "C" __declspec(dllexport)
#else
#define CALIX_API extern "C" __attribute__((visibility("default")))
#endif

namespace {
struct PardisoState {
    const SparseRuntime& runtime;
    void* data[64]{};
    int parameters[64]{};
    int type=11,max_factors=1,factor=1,right_sides=1,message=0,permutation=0;
    int n;
    const double* values;
    const int* rows;
    const int* columns;
    PardisoState(const SparseRuntime& api,int size,const double* a,const int* ia,const int* ja):runtime(api),n(size),values(a),rows(ia),columns(ja) {
        runtime.initialize(data,&type,parameters);
        parameters[1]=3; // Parallel nested dissection.
        parameters[7]=2;
        parameters[26]=1;
        parameters[34]=1; // Zero-based CSR, with full unsymmetric storage.
    }
    int call(int phase,double* b,double* x) {
        int error=0;
        runtime.solve(data,&max_factors,&factor,&type,&phase,&n,values,rows,columns,&permutation,&right_sides,parameters,&message,b,x,&error);
        return error;
    }
    ~PardisoState(){double dummy=0;call(-1,&dummy,&dummy);}
};
struct SparseThreads {
    const SparseRuntime& runtime;
    int previous;
    SparseThreads(const SparseRuntime& api,int count):runtime(api),previous(api.threads(count)){}
    ~SparseThreads(){runtime.threads(previous);}
};
}

// A general sparse solver: no geometry, load case or material is embedded here.
CALIX_API int calix_sparse_solve(int n, int nonzero, const int32_t* row,
    const int32_t* column, const double* entries, const double* rhs,
    double* output, double* residual) {
    if (n<1 || n>400000 || nonzero<1 || !row || !column || !entries ||
        !rhs || !output || !residual) return -1;
    try {
        const auto& runtime=calix_sparse_runtime();
        if(!runtime.module)return -6;
        const int threads=n<512?1:calix_thread_limit();
        SparseThreads thread_scope(runtime,threads);
        using Sparse=Eigen::SparseMatrix<double,Eigen::RowMajor,int>;
        std::vector<Eigen::Triplet<double>> triplets;
        triplets.reserve(nonzero);
        for(int i=0;i<nonzero;++i) {
            if(row[i]<0 || row[i]>=n || column[i]<0 || column[i]>=n ||
                !std::isfinite(entries[i])) return -1;
            triplets.emplace_back(row[i],column[i],entries[i]);
        }
        Sparse matrix(n,n);
        matrix.setFromTriplets(triplets.begin(),triplets.end());
        matrix.makeCompressed();
        Eigen::VectorXd b=Eigen::Map<const Eigen::VectorXd>(rhs,n);
        if(!b.allFinite()) return -1;
        // Symmetric row/column equilibration limits stiffness scale disparities.
        Eigen::VectorXd scale=Eigen::VectorXd::Zero(n);
        for(int k=0;k<matrix.outerSize();++k)
            for(Sparse::InnerIterator it(matrix,k);it;++it)
                scale[it.row()]=std::max(scale[it.row()],std::abs(it.value()));
        for(int i=0;i<n;++i) {
            if(!(scale[i]>0))return -2;
            scale[i]=1/std::sqrt(scale[i]);
        }
        Sparse scaled=matrix;
        for(int k=0;k<scaled.outerSize();++k)
            for(Sparse::InnerIterator it(scaled,k);it;++it)
                it.valueRef()*=scale[it.row()]*scale[it.col()];
        scaled.makeCompressed();
        PardisoState solver(runtime,n,scaled.valuePtr(),scaled.outerIndexPtr(),scaled.innerIndexPtr());
        Eigen::VectorXd scaled_b=scale.asDiagonal()*b,scaled_x(n);
        const int status=solver.call(13,scaled_b.data(),scaled_x.data());
        if(status)return -100-std::abs(status);
        // Perturbed pivots can conceal rank deficiency in unconstrained models.
        if(solver.parameters[13]>0)return -2;
        Eigen::VectorXd x=scale.asDiagonal()*scaled_x;
        if(!x.allFinite())return -3;
        for(int iteration=0;iteration<3;++iteration) {
            Eigen::VectorXd r=b-matrix*x;
            if(r.norm()/std::max(1.,b.norm())<1e-11)break;
            scaled_b=scale.asDiagonal()*r;
            if(solver.call(33,scaled_b.data(),scaled_x.data()))return -3;
            x+=scale.asDiagonal()*scaled_x;
        }
        *residual=(matrix*x-b).norm()/std::max(1.,b.norm());
        if(!std::isfinite(*residual) || *residual>1e-7)return -4;
        Eigen::Map<Eigen::VectorXd>(output,n)=x;
        calix_record_threads(threads);
        return 0;
    }catch(...){return -5;}
}

// Constant tensor coefficients on isoparametric Q1 quadrilaterals / hexahedra.
// Connectivity uses the conventional counter-clockwise bottom/top node order.
CALIX_API int calix_fem_elements(int dimension,int fields,int nodes,int elements,
    int order,const double* coordinates,const int32_t* cells,const double* diffusion,
    const double* reaction,const double* conservative,const double* convection,
    const double* load,double* stiffness,double* force) {
    if((dimension!=2 && dimension!=3) || fields<1 || fields>8 || nodes<1 ||
        elements<1 || elements>100000 || order<1 || order>4 || !coordinates ||
        !cells || !diffusion || !reaction || !conservative || !convection ||
        !load || !stiffness || !force)return -1;
    try {
        const int vertices=1<<dimension,local=vertices*fields;
        const int signs[8][3]={{-1,-1,-1},{1,-1,-1},{1,1,-1},{-1,1,-1},
            {-1,-1,1},{1,-1,1},{1,1,1},{-1,1,1}};
        const int quadrature=order==1?1:order==4?3:2;
        const double abscissa[3][3]={{0,0,0},{-1/std::sqrt(3.),1/std::sqrt(3.),0},
            {-std::sqrt(3./5),0,std::sqrt(3./5)}};
        const double weights[3][3]={{2,0,0},{1,1,0},{5./9,8./9,5./9}};
        return calix_parallel_for(elements,128,[&](int element) {
            Eigen::MatrixXd position(vertices,dimension);
            for(int a=0;a<vertices;++a) {
                int node=cells[element*vertices+a];
                if(node<0 || node>=nodes)return -1;
                for(int b=0;b<dimension;++b)position(a,b)=coordinates[node*dimension+b];
            }
            Eigen::MatrixXd matrix=Eigen::MatrixXd::Zero(local,local);
            Eigen::VectorXd vector=Eigen::VectorXd::Zero(local);
            int orientation=0;
            int count=1;for(int b=0;b<dimension;++b)count*=quadrature;
            for(int point=0;point<count;++point) {
                int index=point;double xi[3]={0,0,0},weight=1;
                for(int b=0;b<dimension;++b) {
                    int q=index%quadrature;index/=quadrature;
                    xi[b]=abscissa[quadrature-1][q];weight*=weights[quadrature-1][q];
                }
                Eigen::VectorXd shape(vertices);
                Eigen::MatrixXd derivative(vertices,dimension);
                for(int a=0;a<vertices;++a) {
                    shape[a]=1.;
                    for(int b=0;b<dimension;++b)shape[a]*=(1+signs[a][b]*xi[b])/2;
                    for(int b=0;b<dimension;++b) {
                        double value=signs[a][b]/2.;
                        for(int c=0;c<dimension;++c)if(c!=b)value*=(1+signs[a][c]*xi[c])/2;
                        derivative(a,b)=value;
                    }
                }
                Eigen::MatrixXd jacobian=position.transpose()*derivative;
                double determinant=jacobian.determinant();
                if(!std::isfinite(determinant) || std::abs(determinant)<1e-14)return -2;
                int sign=determinant>0?1:-1;
                if(orientation && sign!=orientation)return -2;
                orientation=sign;
                Eigen::MatrixXd gradient=derivative*jacobian.inverse();
                weight*=std::abs(determinant);
                for(int a=0;a<vertices;++a)for(int i=0;i<fields;++i) {
                    vector[a*fields+i]+=weight*shape[a]*load[i];
                    for(int b=0;b<vertices;++b)for(int j=0;j<fields;++j) {
                        double value=reaction[i*fields+j]*shape[a]*shape[b];
                        for(int k=0;k<dimension;++k) {
                            value+=conservative[(i*fields+j)*dimension+k]*gradient(a,k)*shape[b]
                                +convection[(i*fields+j)*dimension+k]*shape[a]*gradient(b,k);
                            for(int l=0;l<dimension;++l)
                                value+=diffusion[((i*fields+j)*dimension+k)*dimension+l]*gradient(b,k)*gradient(a,l);
                        }
                        matrix(a*fields+i,b*fields+j)+=weight*value;
                    }
                }
            }
            if(!matrix.allFinite() || !vector.allFinite())return -3;
            for(int i=0;i<local;++i) {
                force[element*local+i]=vector[i];
                for(int j=0;j<local;++j)stiffness[(element*local+i)*local+j]=matrix(i,j);
            }
            return 0;
        });
    }catch(...){return -4;}
}
