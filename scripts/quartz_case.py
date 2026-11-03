"""Oblique TE scattering, conforming Q1 FEM and Bloch-periodic boundaries."""


def notebook(text, calc):
    return {'title': '波动光学：石英与空气的反射和折射', 'component': 'pde', 'cells': [
        text(r'''# 波动光学：石英与空气的反射和折射

波长 $\lambda_0=550\,\mathrm{nm}$ 的单色光从石英射向空气，入射角为 $30^\circ$，界面为 $x=0$。取 $n_q=1.5443,n_a=1,\mu_r=1$，忽略吸收。电场沿 $z$ 方向，石英光轴沿 $y$ 方向，采用普通光的 TE 模型。

以 $\lambda_0$ 为长度单位，计算区域为 $[-3,3]\times[-1.5,1.5]$。界面两侧共用节点，四边形网格在界面连续。

## 控制方程与边界条件

时间约定为 $e^{-i\omega t}$。令 $E_z=u+iv$，两种介质内分别满足

$$-\nabla^2 E_z-(2\pi n)^2E_z=0.$$

切向波数 $s=2\pi n_q\sin\alpha$ 在界面连续。两侧法向波数为 $\kappa=2\pi n_q\cos\alpha$、$\tau=2\pi\sqrt{1-n_q^2\sin^2\alpha}$。左右端采用与此入射模态匹配的辐射条件：

$$\partial_n E_z-i\kappa E_z=-2i\kappa e^{isy}\quad(x=-3),\qquad \partial_n E_z-i\tau E_z=0\quad(x=3).$$

上下边界用 Bloch 周期约束 $E_z(x,1.5)=e^{3is}E_z(x,-1.5)$，相应通量反向。这些边界适用于本例的无限平面波。'''),
        calc('''Clear[a,b,c,d,e,f,g,h,i,j,k,m,n,p,q,r,s,t,u,v,x,y,α,κ,τ];
n=96;a=2*n;b=n;q=15443/10000;α=N[30°];
s=N[2*Pi*q*Sin[α]];κ=N[2*Pi*q*Cos[α]];τ=N[2*Pi*Sqrt[1-q^2*Sin[α]^2]];
p=N[Flatten[Table[{-3+6*i/a,-3/2+3*j/b},{i,0,a},{j,0,b}],1]];
f=Flatten[Table[k=i*(b+1)+j+1;{k,k+b+1,k+b+2,k+1},{i,0,a-1},{j,0,b-1}],1];
m=ToElementMesh["Coordinates"->p,"MeshElements"->{QuadElement[f]}];
Labeled[m["Wireframe"],"quadrilateral mesh, x and y / wavelength"]
Labeled[{Length[p],Length[f]},"nodes and quadrilaterals"]'''),
        text(r'''## 有限元组装

两个介质分别积分，再合并界面自由度。实部与虚部按节点交错排列。辐射边界使用一致边界质量矩阵；上下边界的复相位约束写成实二维旋转。C++ 内核完成体积分和稀疏线性求解。'''),
        calc('''c=Table[Flatten[Table[Part[p,i*(b+1)+j+1],{i,(h-1)*n,h*n},{j,0,b}],1],{h,1,2}];
d=Flatten[Table[k=i*(b+1)+j+1;{k,k+b+1,k+b+2,k+1},{i,0,n-1},{j,0,b-1}],1];
e=Table[ToElementMesh["Coordinates"->j,"MeshElements"->{QuadElement[d]}],{j,c}];
g=Table[Flatten[Table[{2*((h-1)*n*(b+1)+i)-1,2*((h-1)*n*(b+1)+i)},{i,1,Length[Part[c,h]]}]],{h,1,2}];
t=Table[SparseArray[Table[{i,Part[g,h,i]}->1,{i,1,2*Length[Part[c,h]]}],{2*Length[Part[c,h]],2*Length[p]}],{h,1,2}];
k=Table[
 v=NDSolve`VariableData[{"DependentVariables","Space"}->{{u,v},{x,y}}];r=NDSolve`SolutionData[{"Space"}->{Part[e,h]}];
 j=InitializePDEMethodData[v,r,"IntegrationOrder"->2];
 i=InitializePDECoefficients[v,r,"DiffusionCoefficients"->Table[KroneckerDelta[i,j]*KroneckerDelta[k,m],{i,1,2},{j,1,2},{k,1,2},{m,1,2}],"ReactionCoefficients"->Table[-N[4*Pi^2*If[h==1,q^2,1]]*KroneckerDelta[i,j],{i,1,2},{j,1,2}]];
 i=DiscretizePDE[i,j,r];Dot[Transpose[Part[t,h]],i["StiffnessMatrix"],Part[t,h]],{h,1,2}];
k=Part[k,1]+Part[k,2];
d=Flatten[Table[
 c=If[h==0,κ,τ]*3/(6*b);i=2*(h*a*(b+1)+j)+1;
 Join[{{i,i+1}->c*If[j==0||j==b,2,4],{i+1,i}->-c*If[j==0||j==b,2,4]},If[j<b,{{i,i+3}->c,{i+1,i+2}->-c,{i+2,i+1}->c,{i+3,i}->-c},{}]],{h,0,1},{j,0,b}],2];
k=k+SparseArray[d,{2*Length[p],2*Length[p]}];
f=Flatten[Table[If[i==0,κ/b*{
 If[j==0||j==b,2,4]*Sin[s*(-3/2+3*j/b)]+If[j>0,Sin[s*(-3/2+3*(j-1)/b)],0]+If[j<b,Sin[s*(-3/2+3*(j+1)/b)],0],
 -If[j==0||j==b,2,4]*Cos[s*(-3/2+3*j/b)]-If[j>0,Cos[s*(-3/2+3*(j-1)/b)],0]-If[j<b,Cos[s*(-3/2+3*(j+1)/b)],0]}, {0,0}],{i,0,a},{j,0,b}]];
t=SparseArray[Join[
 Flatten[Table[Table[{2*(i*(b+1)+j)+h,2*(i*b+j)+h}->1,{h,1,2}],{i,0,a},{j,0,b-1}],2],
 Flatten[Table[j=2*(i*(b+1)+b);h=2*i*b;{{j+1,h+1}->Cos[3*s],{j+1,h+2}->-Sin[3*s],{j+2,h+1}->Sin[3*s],{j+2,h+2}->Cos[3*s]},{i,0,a}],1]],{2*Length[p],2*(a+1)*b}];
d=Dot[Transpose[t],k,t];f=Dot[Transpose[t],f];v=LinearSolve[d,f];u=Dot[t,v];
Labeled[Norm[Dot[d,v]-f]/Norm[f],"relative algebraic residual"]'''),
        text(r'''## 反射、折射与能流

从左端总场减去入射场，得到反射幅值。右端场强乘以法向波数之比，得到透射能流。输出有限元结果与菲涅耳值，并检查 $R+T-1$。

$$R=|r|^2,\quad T=\frac{\tau}{\kappa}|t|^2,\qquad r=\frac{\kappa-\tau}{\kappa+\tau},\quad t=\frac{2\kappa}{\kappa+\tau}.$$

第一张场图显示总电场，第二张扣除左侧入射场，显示反射波与折射波。箭头分别表示入射、反射和折射的传播方向；坐标以真空波长计。'''),
        calc('''r=Mean[Table[(Part[u,2*j+1]-Cos[s*(-3/2+3*j/b)])^2+(Part[u,2*j+2]-Sin[s*(-3/2+3*j/b)])^2,{j,0,b-1}]];
t=τ/κ*Mean[Table[Part[u,2*(a*(b+1)+j)+1]^2+Part[u,2*(a*(b+1)+j)+2]^2,{j,0,b-1}]];
Labeled[{r,t,r+t-1},"FEM {reflectance, transmittance, energy balance error}"]
Labeled[N[{((κ-τ)/(κ+τ))^2,4*κ*τ/(κ+τ)^2},12],"Fresnel {reflectance, transmittance}"]
Labeled[N[{α,ArcSin[q*Sin[α]]}*180/Pi],"incident and refracted angles [degrees]"]
c=Table[{Part[p,i,1],Part[p,i,2],0},{i,1,Length[p]}];
Labeled[Table[d=Table[Part[u,2*i-1]-If[h==2&&Part[p,i,1]<=0,Cos[κ*(Part[p,i,1]+3)+s*Part[p,i,2]],0],{i,1,Length[p]}];e=Max[Abs[Min[d]],Abs[Max[d]]];
 Labeled[Legended[Graphics3D[{
 GraphicsComplex[c,Polygon[Part[Part[m["MeshElements"],1],1]],VertexColors->Table[ColorData["TemperatureMap"][(Part[d,i]+e)/(2*e)],{i,1,Length[p]}]],
 Style[Line[{{0,-3/2,1/100},{0,3/2,1/100}}],"#263641","interface"],
 Style[Arrow[{{-5/2,-5/2*Tan[α],1/50},{0,0,1/50}}],"#164fa3","incident"],
 Style[Arrow[{{0,0,1/50},{-5/2,5/2*Tan[α],1/50}}],"#b23058","reflected"],
 Style[Arrow[{{0,0,1/50},{6/5,6*s/(5*τ),1/50}}],"#137b45","refracted"]
 }],BarLegend[{"TemperatureMap",{-e,e}},LegendLabel->"Re(Ez)"]],If[h==1,"total electric field","reflected field (left) and refracted field (right)"]],{h,1,2}],"TE electric fields, x and y / wavelength"]''')
    ]}
