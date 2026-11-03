"""Derive Coulomb bound states by coefficient recurrence from the radial ODE."""


def notebook(text,calc):
    return {'title':'类氢离子：薛定谔方程解析解','cells':[
        text(r'''# 类氢离子：薛定谔方程解析解

固定电荷为 $+Ze$ 的原子核，只考虑一个电子。忽略自旋、外场和相对论效应。在原子单位下，定态方程为

$$-\frac12\nabla^2\psi-\frac Zr\psi=E\psi.$$

将角向分离常数记为 $\ell(\ell+1)$。束缚态在原点有限，并且在无穷远可归一化。下面由径向方程确定级数系数、允许的能量和归一化常数，最后取 He⁺，$Z=2$。'''),
        calc('''Clear[r,z,k,ℓ,n,j,a,b,f,h,e,c,u,v,x,y,θ];
e=D[f[r],{r,2}]+2/r*D[f[r],r]+(2*z/r-k^2-ℓ*(ℓ+1)/r^2)*f[r];
Labeled[e==0,"radial Schrodinger equation, E=-k^2/2"]
Labeled[SolveValues[a*(a+1)==ℓ*(ℓ+1),a],"exponents at the origin"]'''),
        text(r'''## 级数与能量

取在原点有限的一支，写成 $R(r)=r^\ell e^{-kr}F(r)$，其中 $k>0$。将这个形式代回径向方程，计算相邻幂次的系数关系。有限多项式可避免无穷远的增长支；多项式次数记为 $j$。'''),
        calc('''u=r^ℓ*Exp[-k*r]*h[r];
v=Simplify[(D[u,{r,2}]+2/r*D[u,r]+(2*z/r-k^2-ℓ*(ℓ+1)/r^2)*u)/(r^(ℓ-1)*Exp[-k*r])];
Labeled[Expand[v]==0,"equation for the remaining radial factor"]
u=a*r^j+b*r^(j+1);
v=Expand[r*D[u,{r,2}]+(2*ℓ+2-2*k*r)*D[u,r]+2*(z-k*(ℓ+1))*u];
c=Coefficient[PowerExpand[v/r^(j-1)],r,1];
Labeled[SolveValues[c==0,b],"coefficient recurrence: b=a_(j+1), a=a_j"]
k=First[SolveValues[z-k*(j+ℓ+1)==0,k]];
Labeled[k,"termination condition"]
Labeled[ReplaceAll[-k^2/2,j->n-ℓ-1],"bound-state energy"]'''),
        text(r'''## He⁺ 的径向函数

分别求 1s、2s、2p、3s、3p 和 3d。级数首项先取 1，逐项用递推式计算，再由径向概率积分确定常数。计算结果同时代回原方程。'''),
        calc('''z=2;
a=Table[
 n=Part[b,1];ℓ=Part[b,2];k=z/n;
 c=Table[Product[2*(k*(j+ℓ+1)-z)/((j+1)*(j+2*ℓ+2)),{j,0,h-1}],{h,0,n-ℓ-1}];
 u=r^ℓ*Exp[-k*r]*Total[Table[Part[c,j+1]*r^j,{j,0,n-ℓ-1}]];
 v=Integrate[u^2*r^2,{r,0,Infinity}];
 Simplify[u/Sqrt[v]],
 {b,{{1,0},{2,0},{2,1},{3,0},{3,1},{3,2}}}];
Labeled[a,"normalized radial functions R_nl"]
Labeled[Table[Integrate[Part[a,j]^2*r^2,{r,0,Infinity}],{j,1,6}],"radial normalization"]
Labeled[Table[n=Part[b,1];ℓ=Part[b,2];u=Part[a,Part[b,3]];Simplify[-(D[u,{r,2}]+2/r*D[u,r]-ℓ*(ℓ+1)*u/r^2)/2-z/r*u+z^2/(2*n^2)*u],{b,{{1,0,1},{2,0,2},{2,1,3},{3,0,4},{3,1,5},{3,2,6}}}],"Schrodinger equation residuals"]'''),
        text(r'''## 概率云

取磁量子数 $m=0$，令 $q=\cos\theta$。角向方程为

$$(1-q^2)Y''-2qY'+\ell(\ell+1)Y=0.$$

将二次多项式代入，分别求 $\ell=0,1,2$ 的正则解，再按球面概率积分归一化。每个原子态使用各自的空间范围与透明度标度；坐标单位为玻尔半径。'''),
        calc('''Clear[ℓ,k,n,j,h,z,q,b,c];
a₂=Table[
 h=b₀+b₁*q+b₂*q^2;
 v=Expand[(1-q^2)*D[h,{q,2}]-2*q*D[h,q]+ℓ*(ℓ+1)*h];
 c=First[Solve[Join[Table[Coefficient[v,q,j]==0,{j,0,2}],{If[ℓ==0,b₀,If[ℓ==1,b₁,b₂]]==1}],{b₀,b₁,b₂}]];
 Simplify[ReplaceAll[h,c]],{ℓ,0,2}];
Labeled[a₂,"angular polynomials from the separated equation"]
b=Table[
 ℓ=Part[c,1];u=Part[a,Part[c,2]];
 h=ReplaceAll[Part[a₂,ℓ+1],q->Cos[θ]];
 v=Simplify[h/Sqrt[2*Pi*Integrate[h^2*Sin[θ],{θ,0,Pi}]]];
 Simplify[ReplaceAll[u^2*v^2,{r->Sqrt[x^2+y^2+z^2],θ->ArcCos[z/Sqrt[x^2+y^2+z^2]]}]],
 {c,{{0,1},{0,2},{1,3},{0,4},{1,5},{2,6}}}];
Labeled[DensityPlot3D[Part[b,1],{x,-3,3},{y,-3,3},{z,-3,3}],"He+, 1s"]
Labeled[DensityPlot3D[Part[b,2],{x,-8,8},{y,-8,8},{z,-8,8}],"He+, 2s"]
Labeled[DensityPlot3D[Part[b,3],{x,-8,8},{y,-8,8},{z,-8,8}],"He+, 2p_z"]
Labeled[DensityPlot3D[Part[b,4],{x,-15,15},{y,-15,15},{z,-15,15}],"He+, 3s"]
Labeled[DensityPlot3D[Part[b,5],{x,-15,15},{y,-15,15},{z,-15,15}],"He+, 3p_z"]
Labeled[DensityPlot3D[Part[b,6],{x,-15,15},{y,-15,15},{z,-15,15}],"He+, 3d_z2"]''')
    ]}
