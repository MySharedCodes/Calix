#include <Eigen/Dense>
#include <cmath>
#include <cstdint>
#include "parallel.h"

#ifdef _WIN32
#define CALIX_API extern "C" __declspec(dllexport)
#else
#define CALIX_API extern "C" __attribute__((visibility("default")))
#endif

CALIX_API int calix_fem_triangles(int fields,int nodes,int elements,int order,
    const double* points,const int32_t* cells,const double* diffusion,
    const double* reaction,const double* conservative,const double* convection,
    const double* load,double* stiffness,double* force) {
    if(fields<1 || fields>8 || nodes<3 || elements<1 || elements>100000 || order<1 || order>4 ||
       !points || !cells || !diffusion || !reaction || !conservative || !convection || !load || !stiffness || !force)return -1;
    const int local=3*fields;
    Eigen::Matrix<double,3,2> reference;
    reference<<-1,-1,1,0,0,1;
    return calix_parallel_for(elements,128,[&](int element) {
        Eigen::Matrix<double,3,2> position;
        for(int a=0;a<3;++a) {
            int node=cells[3*element+a];if(node<0 || node>=nodes)return -1;
            for(int d=0;d<2;++d)position(a,d)=points[2*node+d];
        }
        Eigen::Matrix2d jacobian=position.transpose()*reference;
        double determinant=jacobian.determinant();
        if(!std::isfinite(determinant) || std::abs(determinant)<1e-18)return -2;
        double area=std::abs(determinant)/2;
        Eigen::Matrix<double,3,2> gradient=reference*jacobian.inverse();
        for(int a=0;a<3;++a)for(int i=0;i<fields;++i) {
            force[element*local+a*fields+i]=area/3*load[i];
            for(int b=0;b<3;++b)for(int j=0;j<fields;++j) {
                double value=reaction[i*fields+j]*area*(order==1?1./9:(a==b?1./6:1./12));
                for(int k=0;k<2;++k) {
                    value+=area/3*(conservative[(i*fields+j)*2+k]*gradient(a,k)+convection[(i*fields+j)*2+k]*gradient(b,k));
                    for(int l=0;l<2;++l)value+=area*diffusion[((i*fields+j)*2+k)*2+l]*gradient(b,k)*gradient(a,l);
                }
                stiffness[(element*local+a*fields+i)*local+b*fields+j]=value;
            }
        }
        return 0;
    });
}
