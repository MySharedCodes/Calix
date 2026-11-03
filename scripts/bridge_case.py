"""Explicit coefficient FEM and sparse assembly using standard WL names."""


def notebook(text,calc):
    return {'title':'吊桥：混合维有限元受力分析','component':'pde','cells':[
    text(r'''# 吊桥：混合维有限元受力分析

## 桥体与载荷

桥长 $L=80\,\mathrm m$、宽 $B=10\,\mathrm m$，桥塔高 $H=24\,\mathrm m$，桥面位于 $z=H/2$。四根方形桥塔在 $x=\pm L/4,y=\pm B/2$，截面边长 $0.045H$。塔体为混凝土，$E_t=30\,\mathrm{GPa},\nu_t=0.2$；桥面为厚 $t=0.18\,\mathrm m$ 的等效钢板，$E=200\,\mathrm{GPa},\nu=0.3$。

两侧主缆面积 $A_c=0.025\,\mathrm{m^2}$，吊杆面积 $A_h=0.003\,\mathrm{m^2}$。每侧七根吊杆，位置固定为 $x=-3L/8,\ldots,3L/8$。主跨缆线为抛物线，跨中垂度 $H/4$。在已张紧的平衡构型上施加附加压力 $q=1000\,\mathrm{Pa}$，求增量位移。初始张力按恒载 $q_0=2000\,\mathrm{Pa}$ 估计；不包含恒载找形。

塔底、桥面两端及主缆端点固定。同坐标节点共享平移自由度，桥面另有两个转角自由度。塔顶为节点连接，连接处的局部应力需要进一步细化连接模型。'''),
    calc('''Clear[L,B,H,n,x,y,z,i,j,k,a,b,c,d,e,f,g,h,m,p,q,r,s,t,u,v,w];
L=80;B=10;H=24;n=8;q=1000;
e=200000000000;v=3/10;t=18/100;
a=8*n;b=2*n;c=4;d=4*n;
p=Flatten[Table[{L*(i/a-1/2),B*(j/b-1/2)},{i,0,a},{j,0,b}],1];
f=Flatten[Table[k=i*(b+1)+j+1;{k,k+b+1,k+b+2,k+1},{i,0,a-1},{j,0,b-1}],1];
m=ToElementMesh["Coordinates"->p,"MeshElements"->{QuadElement[f]}];
Labeled[{Length[p],Length[f]},"deck nodes and quadrilaterals"]'''),
    text(r'''## 桥面

采用 Reissner–Mindlin 板，节点未知量为 $(u,v,w,\theta_x,\theta_y)$。中面膜应变与曲率分别由平移梯度和转角梯度给出，横向剪切为 $\boldsymbol\gamma=\nabla w-\boldsymbol\theta$。

$$\Pi_d=\frac12\int_{\Omega_d}\left[t\,\boldsymbol\varepsilon:\mathbb C_p:\boldsymbol\varepsilon+\boldsymbol\kappa:\mathbb D:\boldsymbol\kappa+\kappa_sGt\,|\nabla w-\boldsymbol\theta|^2\right]\,\mathrm dA+\int_{\Omega_d}q w\,\mathrm dA.$$

取 $\kappa_s=5/6$。下面将膜、弯曲和剪切项写成系数张量。剪切采用选择性减缩积分，并保留 $10^{-5}$ 的全积分项抑制零能模式；网格比较时这个系数保持不变。'''),
    calc('''s=NDSolve`VariableData[{"DependentVariables","Space"}->{{u,v,w,h,k},{x,y}}];
r=NDSolve`SolutionData[{"Space"}->{m}];
h=e*t^3/(12*(1-v^2));k=5*e*t/(12*(1+v));
c₁=Table[If[i<=2&&j<=2,e*t/(1-v^2)*(v*KroneckerDelta[i,k₂]*KroneckerDelta[j,k₁]+(1-v)/2*(KroneckerDelta[i,j]*KroneckerDelta[k₁,k₂]+KroneckerDelta[i,k₁]*KroneckerDelta[j,k₂])),If[i>=4&&j>=4,h*(v*KroneckerDelta[i-3,k₂]*KroneckerDelta[j-3,k₁]+(1-v)/2*(KroneckerDelta[i,j]*KroneckerDelta[k₁,k₂]+KroneckerDelta[i-3,k₁]*KroneckerDelta[j-3,k₂])),0]],{i,1,5},{j,1,5},{k₁,1,2},{k₂,1,2}];
c₂=Table[If[i==3&&j==3,k*KroneckerDelta[k₁,k₂],0],{i,1,5},{j,1,5},{k₁,1,2},{k₂,1,2}];
a₁=Table[If[i==j&&i>=4,k,0],{i,1,5},{j,1,5}];
b₁=Table[If[i==3&&j==k₁+3,-k,0],{i,1,5},{j,1,5},{k₁,1,2}];
b₂=Table[If[j==3&&i==k₁+3,-k,0],{i,1,5},{j,1,5},{k₁,1,2}];
d₁=InitializePDECoefficients[s,r,"DiffusionCoefficients"->c₁,"LoadCoefficients"->{0,0,-q,0,0}];
d₂=InitializePDECoefficients[s,r,"DiffusionCoefficients"->c₂,"ReactionCoefficients"->a₁,"ConservativeConvectionCoefficients"->b₁,"ConvectionCoefficients"->b₂];
h₁=InitializePDEMethodData[s,r,"IntegrationOrder"->2];
h₂=InitializePDEMethodData[s,r,"IntegrationOrder"->1];
d₁=DiscretizePDE[d₁,h₁,r];
d₃=DiscretizePDE[d₂,h₁,r];
d₂=DiscretizePDE[d₂,h₂,r];
k₁=d₁["StiffnessMatrix"]+99999/100000*d₂["StiffnessMatrix"]+1/100000*d₃["StiffnessMatrix"];
f₁=d₁["LoadVector"];'''),
    text(r'''## 桥塔与索

塔体使用结构化六面体单元，控制方程为 $-\nabla\cdot\boldsymbol\sigma=0$，其中

$$\boldsymbol\sigma=2\mu_t\boldsymbol\varepsilon+\lambda_t\operatorname{tr}(\boldsymbol\varepsilon)\boldsymbol I,\qquad \boldsymbol\varepsilon=\tfrac12(\nabla\boldsymbol u+\nabla\boldsymbol u^{\mathsf T}).$$

索采用预张紧桁架。每段长度 $\ell$、方向 $\boldsymbol n$ 的切线刚度为

$$\boldsymbol k_e=\frac{EA}{\ell}\boldsymbol n\boldsymbol n^{\mathsf T}+\frac{T_0}{\ell}(\boldsymbol I-\boldsymbol n\boldsymbol n^{\mathsf T}).$$

主缆初张力取 $T_c=q_0BL^2/(8H)$，吊杆取 $T_h=q_0BL/16$。这些张力只用于本次增量刚度。'''),
    calc('''c=4;d=4*n;
p₂=Table[Flatten[Table[{Part[j,1]+9*H/400*(2*i/c-1),Part[j,2]+9*H/400*(2*k/c-1),H*h/d},{i,0,c},{k,0,c},{h,0,d}],2],{j,{{-L/4,-B/2},{-L/4,B/2},{L/4,-B/2},{L/4,B/2}}}];
f₂=Flatten[Table[h=i*(c+1)*(d+1)+j*(d+1)+k+1;{h,h+(c+1)*(d+1),h+(c+2)*(d+1),h+d+1,h+1,h+(c+1)*(d+1)+1,h+(c+2)*(d+1)+1,h+d+2},{i,0,c-1},{j,0,c-1},{k,0,d-1}],2];
m₂=Table[ToElementMesh["Coordinates"->j,"MeshElements"->{HexahedronElement[f₂]}],{j,p₂}];
c₃=Table[30000000000*(KroneckerDelta[i,k₂]*KroneckerDelta[j,k₁]/(6/5*3)+5/12*(KroneckerDelta[i,j]*KroneckerDelta[k₁,k₂]+KroneckerDelta[i,k₁]*KroneckerDelta[j,k₂])),{i,1,3},{j,1,3},{k₁,1,3},{k₂,1,3}];
k₂=Table[
 s=NDSolve`VariableData[{"DependentVariables","Space"}->{{u,v,w},{x,y,z}}];r=NDSolve`SolutionData[{"Space"}->{j}];
 h=InitializePDEMethodData[s,r,"IntegrationOrder"->2];c=InitializePDECoefficients[s,r,"DiffusionCoefficients"->c₃];c=DiscretizePDE[c,h,r];c["StiffnessMatrix"],{j,m₂}];
p₃=Table[Table[{L*(i/a-1/2),j*B/2,If[Abs[L*(i/a-1/2)]<=L/4,H-H/4*(1-(4*(i/a-1/2))^2),H-(H/2)*(4*Abs[i/a-1/2]-1)]},{i,0,a}],{j,{-1,1}}];
l=Join[Flatten[Table[{Part[p₃,j,i],Part[p₃,j,i+1]},{j,1,2},{i,1,a}],1],Flatten[Table[{Part[p₃,j,i*n+1],{L*(i/8-1/2),(2*j-3)*B/2,H/2}},{j,1,2},{i,1,7}],1]];
g=Union[Join[Table[{Part[j,1],Part[j,2],H/2},{j,p}],Flatten[p₂,1],Flatten[l,1]]];
h=3*Length[g]+2*Length[p];
Labeled[{Total[Table[Length[f₂],{i,1,4}]],Length[f],Length[l],h},"hexahedra, quadrilaterals, trusses and global DOF"]'''),
    text(r'''## 组装与求解

各子域先独立组装，再由布尔映射矩阵 $\boldsymbol T$ 合并公共平移自由度。约束后的线性系统由 C++ Eigen 求解。

$$\boldsymbol K=\sum_b\boldsymbol T_b^{\mathsf T}\boldsymbol K_b\boldsymbol T_b,\qquad\boldsymbol K_{ff}\boldsymbol u_f=\boldsymbol f_f.$$

输出线性系统残差和应变能，检查离散方程是否满足。残差不能代替网格收敛检验。'''),
    calc('''j=Flatten[Table[k=First[Nearest[g->"Index",{Part[p,i,1],Part[p,i,2],H/2}]];{3*k-2,3*k-1,3*k,3*Length[g]+2*i-1,3*Length[g]+2*i},{i,1,Length[p]}]];
t₁=SparseArray[Table[{i,Part[j,i]}->1,{i,1,Length[j]}],{Length[j],h}];
K=Dot[Transpose[t₁],k₁,t₁];F=Dot[Transpose[t₁],f₁];
k₃=Table[j=Flatten[Table[k=First[Nearest[g->"Index",i]];{3*k-2,3*k-1,3*k},{i,Part[p₂,b]}]];r=SparseArray[Table[{i,Part[j,i]}->1,{i,1,Length[j]}],{Length[j],h}];Dot[Transpose[r],Part[k₂,b],r],{b,1,4}];
K=K+Total[k₃];
k₄=Table[
 p₄=Part[l,b];r=Table[Part[p₄,2,i]-Part[p₄,1,i],{i,1,3}];s=Norm[r];r=Table[Part[r,i]/s,{i,1,3}];
 A=If[b<=2*a,25/1000,3/1000];T=If[b<=2*a,2000*B*L^2/(8*H),2000*B*L/16];
 c=Table[If[Floor[(i-1)/3]==Floor[(j-1)/3],1,-1]*(e*A/s*Part[r,Mod[i-1,3]+1]*Part[r,Mod[j-1,3]+1]+T/s*(KroneckerDelta[Mod[i-1,3],Mod[j-1,3]]-Part[r,Mod[i-1,3]+1]*Part[r,Mod[j-1,3]+1])),{i,1,6},{j,1,6}];
 j=Flatten[Table[k=First[Nearest[g->"Index",i]];{3*k-2,3*k-1,3*k},{i,p₄}]];
 r=SparseArray[Table[{i,Part[j,i]}->1,{i,1,6}],{6,h}];Dot[Transpose[r],c,r],{b,1,Length[l]}];
K=K+Total[k₄];
j=Flatten[Table[If[Part[g,i,3]==0||Abs[Part[g,i,1]]==L/2,{3*i-2,3*i-1,3*i},Nothing],{i,1,Length[g]}]];
j=Union[Join[j,Flatten[Table[If[Abs[Part[p,i,1]]==L/2,{3*Length[g]+2*i-1,3*Length[g]+2*i},Nothing],{i,1,Length[p]}]]]];
r=Complement[Range[h],j];
u=LinearSolve[Part[K,r,r],Part[F,r]];
t₂=SparseArray[Table[{Part[r,i],i}->1,{i,1,Length[r]}],{h,Length[r]}];u=Dot[t₂,u];
Labeled[Norm[Part[Dot[K,u]-F,r]]/Norm[Part[F,r]],"relative residual"]
Labeled[Dot[u,F]/2,"strain energy [J]"]
w=Table[k=First[Nearest[g->"Index",{Part[p,i,1],Part[p,i,2],H/2}]];Part[u,3*k],{i,1,Length[p]}];
Labeled[Min[w],"minimum deck displacement [m]"]
r₁=Dot[K,u]-F;
Labeled[Abs[Total[Table[Part[r₁,3*i],{i,1,Length[g]}]]-q*L*B]/(q*L*B),"vertical force balance, relative error"]
a₁=Table[
 p₄=Part[l,b];r=Table[Part[p₄,2,i]-Part[p₄,1,i],{i,1,3}];s=Norm[r];
 j=Table[First[Nearest[g->"Index",Part[p₄,i]]],{i,1,2}];
 A=If[b<=2*a,25/1000,3/1000];T=If[b<=2*a,2000*B*L^2/(8*H),2000*B*L/16];
 T+e*A/s^2*Total[Table[Part[r,i]*(Part[u,3*Part[j,2]-3+i]-Part[u,3*Part[j,1]-3+i]),{i,1,3}]],{b,1,Length[l]}];
Labeled[Min[a₁],"minimum total cable tension [N]"]'''),
    text(r'''## 网格与变形

第一幅为原始网格，第二幅将桥面、桥塔和索的位移放大 100 倍。修改首个单元的 $n$ 后重新计算，可比较桥面下挠和应变能；吊杆数量与位置不会随网格改变。

模型为线弹性增量分析。若增量轴力使索的总张力降至零，应改为包含索松弛和几何非线性的模型。'''),
    calc('''p₅=Table[{Part[j,1],Part[j,2],H/2},{j,p}];
m₁=ToElementMesh["Coordinates"->p₅,"MeshElements"->{QuadElement[f]}];
p₆=Union[Flatten[l,1]];
f₃=Table[Table[First[Nearest[p₆->"Index",Part[j,i]]],{i,1,2}],{j,l}];
m₃=ToElementMesh["Coordinates"->p₆,"MeshElements"->{LineElement[f₃]}];
Labeled[Show[m₁["Wireframe"],Part[m₂,1]["Wireframe"],Part[m₂,2]["Wireframe"],Part[m₂,3]["Wireframe"],Part[m₂,4]["Wireframe"],m₃["Wireframe"]],"finite-element mesh"]
p₇=Table[k=First[Nearest[g->"Index",j]];Table[Part[j,i]+100*Part[u,3*k-3+i],{i,1,3}],{j,p₅}];
m₄=ToElementMesh["Coordinates"->p₇,"MeshElements"->{QuadElement[f]}];
p₈=Table[k=First[Nearest[g->"Index",j]];Table[Part[j,i]+100*Part[u,3*k-3+i],{i,1,3}],{j,p₆}];
m₅=ToElementMesh["Coordinates"->p₈,"MeshElements"->{LineElement[f₃]}];
u₂=Table[Table[k=First[Nearest[g->"Index",j]];Table[Part[u,3*k-3+i],{i,1,3}],{j,Part[p₂,b]}],{b,1,4}];
m₆=Table[ToElementMesh["Coordinates"->Table[Table[Part[p₂,b,j,i]+100*Part[u₂,b,j,i],{i,1,3}],{j,1,Length[Part[p₂,b]]}],"MeshElements"->{HexahedronElement[f₂]}],{b,1,4}];
Labeled[Show[m₄["Wireframe"],m₅["Wireframe"],Part[m₆,1]["Wireframe"],Part[m₆,2]["Wireframe"],Part[m₆,3]["Wireframe"],Part[m₆,4]["Wireframe"]],"bridge displacement, scale 100"]'''),
    text(r'''## 应力

由单元中心的位移梯度计算应变，桥塔按三维弹性本构关系计算 von Mises 应力。桥面显示膜应力与弯曲应力叠加后的面内 von Mises 应力，取上下表面的较大值：

$$\sigma_x^{\pm}=\frac{E}{1-\nu^2}\left[\varepsilon_x+\nu\varepsilon_y\pm\frac t2(\kappa_x+\nu\kappa_y)\right],\qquad
\sigma_y^{\pm}=\frac{E}{1-\nu^2}\left[\varepsilon_y+\nu\varepsilon_x\pm\frac t2(\kappa_y+\nu\kappa_x)\right].$$

$$\sigma_{\mathrm{vm}}=\sqrt{\frac{(\sigma_x-\sigma_y)^2+(\sigma_y-\sigma_z)^2+(\sigma_z-\sigma_x)^2+6(\tau_{xy}^2+\tau_{yz}^2+\tau_{zx}^2)}2}.$$

单元结果向相邻节点取平均后着色，几何采用未变形位置。桥面、桥塔显示附加载荷产生的应力；索显示含初张力的轴向应力。色标单位为 MPa。塔顶节点连接处的局部峰值受连接模型和网格影响。'''),
    calc('''u₁=ArrayReshape[Dot[t₁,u],{Length[p],5}];
g₁={{-1/4,-1/4},{1/4,-1/4},{1/4,1/4},{-1/4,1/4}};
g₂={{-1/8,-1/8,-1/8},{1/8,-1/8,-1/8},{1/8,1/8,-1/8},{-1/8,1/8,-1/8},{-1/8,-1/8,1/8},{1/8,-1/8,1/8},{1/8,1/8,1/8},{-1/8,1/8,1/8}};
s₁=Table[
 a=Dot[Transpose[Table[Part[u₁,Part[j,i]],{i,1,4}]],g₁,Inverse[Dot[Transpose[Table[Part[p,Part[j,i]],{i,1,4}]],g₁]]];
 c=Table[
  d₁=e/(1-v^2)*(Part[a,1,1]+v*Part[a,2,2]+k*t/2*(Part[a,4,1]+v*Part[a,5,2]));
  d₂=e/(1-v^2)*(Part[a,2,2]+v*Part[a,1,1]+k*t/2*(Part[a,5,2]+v*Part[a,4,1]));
  d₃=e/(2*(1+v))*(Part[a,1,2]+Part[a,2,1]+k*t/2*(Part[a,4,2]+Part[a,5,1]));
  Sqrt[d₁^2+d₂^2-d₁*d₂+3*d₃^2],{k,{-1,1}}];
 Max[c],{j,f}];
d₄=SparseArray[Flatten[Table[Table[{Part[f,j,i],j}->1,{i,1,4}],{j,1,Length[f]}],1],{Length[p],Length[f]}];
s₁=Dot[d₄,s₁]/Dot[d₄,ConstantArray[1,Length[f]]];
d₅=SparseArray[Flatten[Table[Table[{Part[f₂,j,i],j}->1,{i,1,8}],{j,1,Length[f₂]}],1],{Length[Part[p₂,1]],Length[f₂]}];
s₂=Table[
 c=Table[
  a=Dot[Transpose[Table[Part[u₂,b,Part[j,i]],{i,1,8}]],g₂,Inverse[Dot[Transpose[Table[Part[p₂,b,Part[j,i]],{i,1,8}]],g₂]]];
  r=Total[Table[Part[a,i,i],{i,1,3}]];
  a=Table[12500000000*(Part[a,i,k]+Part[a,k,i])+25000000000/3*r*KroneckerDelta[i,k],{i,1,3},{k,1,3}];
  Sqrt[((Part[a,1,1]-Part[a,2,2])^2+(Part[a,2,2]-Part[a,3,3])^2+(Part[a,3,3]-Part[a,1,1])^2+6*(Part[a,1,2]^2+Part[a,2,3]^2+Part[a,3,1]^2))/2],{j,f₂}];
 r=Dot[d₅,c]/Dot[d₅,ConstantArray[1,Length[f₂]]];
 Table[Part[r,i],{i,1,Length[Part[p₂,b]]}],{b,1,4}];
s₃=Table[Part[a₁,b]/If[b<=2*Length[Part[p₃,1]]-2,25/1000,3/1000],{b,1,Length[l]}];
c=Max[Join[Table[Part[s₁,i],{i,1,Length[p]}],Flatten[s₂],s₃]];
Labeled[{Max[s₁]/10^6,Max[Flatten[s₂]]/10^6,Max[s₃]/10^6},"maximum nodal stress, {deck, towers, cables} [MPa]"]
Labeled[Legended[Graphics3D[{
 GraphicsComplex[p₅,Polygon[f],VertexColors->Table[ColorData["TemperatureMap"][Part[s₁,i]/c],{i,1,Length[p]}]],
 Table[GraphicsComplex[Part[p₂,b],Polygon[Part[Part[Part[m₂,b]["BoundaryElements"],1],1]],VertexColors->Table[ColorData["TemperatureMap"][Part[s₂,b,i]/c],{i,1,Length[Part[p₂,b]]}]],{b,1,4}],
 Table[Style[Line[Part[l,b]],ColorData["TemperatureMap"][Part[s₃,b]/c]],{b,1,Length[l]}]
}],BarLegend[{"TemperatureMap",{0,c/10^6}},LegendLabel->"von Mises / axial stress [MPa]"]],"bridge stress"]''')
    ]}
