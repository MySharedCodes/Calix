"""Unequal filleted involute gears, unstructured FEM and weighted contact."""


def notebook(text,calc):
    return {'title':'齿轮啮合：接触与扭矩传递','component':'pde','cells':[
        text(r'''# 齿轮啮合：接触与扭矩传递

小齿轮驱动大齿轮，齿数分别为 $z_1=20,z_2=40$，模数 $m=2\,\mathrm{mm}$，压力角 $\alpha=20^\circ$，齿宽 $b=10\,\mathrm{mm}$。节圆半径分别为 $20\,\mathrm{mm}$ 和 $40\,\mathrm{mm}$，中心距 $60\,\mathrm{mm}$。材料取 $E=210\,\mathrm{GPa},\nu=0.3$。

本例为二维直齿轮平面应力分析。小齿轮孔边施加顺时针转角 $\delta=10^{-4}$ rad，大齿轮孔边固定，求这一啮合位置的静态接触载荷与应力。

## 齿廓、圆角与非结构网格

渐开线齿面满足

$$r=r_b\sqrt{1+t^2},\qquad \varphi=\pm\left(\frac{\pi}{2z}+\tan\alpha-\alpha-t+\arctan t\right).$$

齿根圆角半径取 $0.7\,\mathrm{mm}$，与齿根圆及齿面相切。小齿轮基圆以下保留短直线过渡，再与圆角相切。孔半径为各自节圆半径的 0.35 倍。

以小齿轮节圆半径为长度单位。BoundaryMeshRegion 定义外齿廓和内孔，ToElementMesh 生成非结构三角形网格。MeshRefinementFunction 在接触区和各齿根圆角附近加密；$\eta$ 控制整体网格尺度，减小后重新计算可检查收敛。'''),
        calc('''Clear[a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v,w,x,y,z,α,β,δ,η,ρ,φ,θ,τ];
α=N[20°];δ=1/10000;η=1;ρ=7/200;n=12;
m=Table[
 z=Part[{20,40},h];r=Part[{1,2},h];a=r+1/10;c=r-1/8;b=r*Cos[α];
 v=Pi/(2*z)+Tan[α]-α;
 τ=If[c+ρ>Sqrt[b^2+ρ^2],(Sqrt[(c+ρ)^2-b^2]-ρ)/b,0];
 g=If[τ>0,b*Sqrt[1+τ^2],Sqrt[c^2+2*c*ρ]];
 φ=-v+τ-ArcTan[τ];θ=-v+τ;
 q={g*Cos[φ]+ρ*Sin[θ],g*Sin[φ]-ρ*Cos[θ]};
 β=ArcTan[Part[q,1],Part[q,2]];
 s=Sqrt[a^2/b^2-1];
 d=Flatten[Table[
  t=Sort[Join[Table[If[i==If[h==1,0,z/2]&&Abs[τ+(s-τ)*j/n-Tan[α]]<36/1000,Nothing,N[τ+(s-τ)*j/n]],{j,0,n}],
   If[i==If[h==1,0,z/2],Table[Tan[α]+j/2000,{j,-70,70}],{}]]];
  l=Join[
   Table[q+ρ*{Cos[Pi+β+(-v+τ-Pi/2-β)*j/8],Sin[Pi+β+(-v+τ-Pi/2-β)*j/8]},{j,0,7}],
   If[τ==0,Table[(g+(b-g)*j/2)*{Cos[-v],Sin[-v]},{j,0,1}],{}],
   Table[b*Sqrt[1+j^2]*{Cos[-v+j-ArcTan[j]],Sin[-v+j-ArcTan[j]]},{j,t}]];
  l=Join[
   Table[c*{Cos[-Pi/z+(β+Pi/z)*j/4],Sin[-Pi/z+(β+Pi/z)*j/4]},{j,0,3}],
   l,
   Table[a*{Cos[-v+s-ArcTan[s]+2*(v-s+ArcTan[s])*j/6],Sin[-v+s-ArcTan[s]+2*(v-s+ArcTan[s])*j/6]},{j,1,5}],
   Table[{Part[l,j,1],-Part[l,j,2]},{j,Length[l],1,-1}],
   Table[c*{Cos[-β+(Pi/z+β)*j/4],Sin[-β+(Pi/z+β)*j/4]},{j,1,3}]];
  θ=2*Pi*i/z+Pi/(2*z);
  Table[{3*(h-1)+Part[j,1]*Cos[θ]-Part[j,2]*Sin[θ],Part[j,1]*Sin[θ]+Part[j,2]*Cos[θ]},{j,l}]
 ,{i,0,z-1}],1];
 a=Length[d];o=96;
 p=N[Join[d,Table[{3*(h-1)+7*r/20*Cos[-2*Pi*j/o],7*r/20*Sin[-2*Pi*j/o]},{j,0,o-1}]]];
 f=Join[Table[{j,Mod[j,a]+1},{j,1,a}],Table[{a+j,a+Mod[j,o]+1},{j,1,o}]];
 r=Flatten[Table[Table[
  θ=2*Pi*i/z+Pi/(2*z);
  l=q+ρ*{Cos[Pi+β+(-v+τ-Pi/2-β)/2],Sin[Pi+β+(-v+τ-Pi/2-β)/2]};
  l={Part[l,1],j*Part[l,2]};
  {3*(h-1)+Part[l,1]*Cos[θ]-Part[l,2]*Sin[θ],Part[l,1]*Sin[θ]+Part[l,2]*Cos[θ]}
 ,{j,{-1,1}}],{i,0,z-1}],1];
 ToElementMesh[BoundaryMeshRegion[p,{LineElement[f]}],MaxCellMeasure->η^2/200,
  MeshRefinementFunction->Function[{v,a},a>η^2/(200+10/(Norm[Mean[v]-{1,0}]^2+1/10000000)+
   Total[Table[2/(Norm[Mean[v]-Part[r,j]]^2+1/100000),{j,1,Length[r]}]])],MeshOrder->1]
,{h,1,2}];
p=Table[Part[m,h]["Coordinates"],{h,1,2}];
f=Table[Part[Part[Part[m,h]["MeshElements"],1],1],{h,1,2}];
l=Table[Part[Part[Part[m,h]["BoundaryElements"],1],1],{h,1,2}];
Labeled[Show[Part[m,1]["Wireframe"],Part[m,2]["Wireframe"]],"unstructured meshes, pinion left and driven gear right"]
Labeled[Table[{Length[Part[p,h]],Length[Part[f,h]]},{h,1,2}],"nodes and triangles, {pinion, gear}"]'''),
        text(r'''## 弹性与齿面接触

各齿轮内部满足 $-\nabla\cdot\boldsymbol\sigma=0$，平面应力本构为

$$\boldsymbol\sigma=2\mu\boldsymbol\varepsilon+\lambda_p\operatorname{tr}(\boldsymbol\varepsilon)\boldsymbol I,\quad
\mu=\frac{1}{2(1+\nu)},\quad \lambda_p=\frac{\nu}{1-\nu^2}.$$

小齿轮齿面节点投影到大齿轮边界线段。以 $g_0$ 表示初始间隙，$\boldsymbol n$ 指向大齿轮内部，位移后的间隙及压力为

$$g=g_0+\boldsymbol n\cdot(\boldsymbol u_2-\boldsymbol u_1),\qquad p_n=\gamma\max(0,-g).$$

取 $\gamma=10^6$。节点的接触积分权重为相邻齿面线段长度之和的一半，节点力为 $p_nw$，而非将压力直接作为节点力。三角形单元积分和稀疏方程求解使用 C++ 内核。'''),
        calc('''v=3/10;
c=Table[v/(1-v^2)*KroneckerDelta[i,l]*KroneckerDelta[j,k]+1/(2*(1+v))*(KroneckerDelta[i,j]*KroneckerDelta[k,l]+KroneckerDelta[i,k]*KroneckerDelta[j,l]),{i,1,2},{j,1,2},{k,1,2},{l,1,2}];
k=Table[s=NDSolve`VariableData[{"DependentVariables","Space"}->{{u,v},{x,y}}];r=NDSolve`SolutionData[{"Space"}->{Part[m,h]}];t=InitializePDEMethodData[s,r,"IntegrationOrder"->2];d=InitializePDECoefficients[s,r,"DiffusionCoefficients"->c];d=DiscretizePDE[d,t,r];d["StiffnessMatrix"],{h,1,2}];
k=ArrayFlatten[{{Part[k,1],0},{0,Part[k,2]}}];
e=Length[Part[p,1]];q=Join[Part[p,1],Part[p,2]];
l₂=Table[If[Abs[Part[p,2,Part[j,1],1]-1]<1/5&&Abs[Part[p,2,Part[j,1],2]]<1/5,j,Nothing],{j,Part[l,2]}];
d=Union[Flatten[l₂]];a=Union[Flatten[Part[l,1]]];
r=Table[Part[p,2,j],{j,d}];
c=Table[If[Abs[Part[p,1,i,1]-1]<1/8&&Abs[Part[p,1,i,2]]<1/8,
 w=Part[p,1,i];j=Part[d,First[Nearest[r->"Index",w]]];
 t=Table[If[Part[v,1]==j||Part[v,2]==j,
  u=Part[p,2,Part[v,1]];s=Part[p,2,Part[v,2]];o=Max[0,Min[1,Dot[w-u,s-u]/Dot[s-u,s-u]]];
  {Norm[u+o*(s-u)-w],Part[v,1],Part[v,2],o},Nothing],{v,l₂}];
 t=First[Sort[t]];u=Part[p,2,Part[t,2]];v=Part[p,2,Part[t,3]];
 s={-(Part[v,2]-Part[u,2]),Part[v,1]-Part[u,1]};s=s/Norm[s];
 o=Dot[s,u+Part[t,4]*(v-u)-w];
 If[Part[s,1]>1/10&&Abs[o]<1/500,
  v=Total[Table[If[Part[j,1]==i||Part[j,2]==i,Norm[Part[p,1,Part[j,1]]-Part[p,1,Part[j,2]]]/2,0],{j,Part[l,1]}]];
  {i,e+Part[t,2],e+Part[t,3],Part[t,4],Part[s,1],Part[s,2],o,v},Nothing],Nothing],{i,a}];
Labeled[{Length[c],Min[Table[Part[j,7],{j,c}]]},"contact candidates and minimum initial gap / rp1"]'''),
        calc('''g=SparseArray[Flatten[Table[j=Part[c,i];Flatten[Table[{{i,2*Part[j,1]-2+h}->-Part[j,4+h],{i,2*Part[j,2]-2+h}->(1-Part[j,4])*Part[j,4+h],{i,2*Part[j,3]-2+h}->Part[j,4]*Part[j,4+h]},{h,1,2}],1],{i,1,Length[c]}],1],{Length[c],2*Length[q]}];
h=Table[Part[j,7],{j,c}];b=Table[Part[j,8],{j,c}];
d₁=Table[If[Norm[Part[p,1,i]]<=7/20+1/1000000,i,Nothing],{i,Union[Flatten[Part[l,1]]]}];
d₂=Table[If[Norm[Part[p,2,i]-{3,0}]<=7/10+1/1000000,e+i,Nothing],{i,Union[Flatten[Part[l,2]]]}];
d=Flatten[Table[{2*i-1,2*i},{i,Join[d₁,d₂]}]];r=Complement[Range[2*Length[q]],d];
t=SparseArray[Table[{Part[r,i],i}->1,{i,1,Length[r]}],{2*Length[q],Length[r]}];
w=Table[If[i<=2*e,If[Mod[i,2]==1,δ*Part[q,(i+1)/2,2],-δ*Part[q,i/2,1]],0],{i,1,2*Length[q]}];
w=Dot[SparseArray[Table[{i,Part[d,i]}->1,{i,1,Length[d]}],{Length[d],2*Length[q]}],w];
w=Dot[SparseArray[Table[{Part[d,i],i}->1,{i,1,Length[d]}],{2*Length[q],Length[d]}],w];u=w;
s=Table[
 v=h+Dot[g,u];
 j=SparseArray[Table[{i,i}->If[Part[v,i]<0,1000000*Part[b,i],0],{i,1,Length[c]}],{Length[c],Length[c]}];
 o=k+Dot[Transpose[g],j,g];
 v=-Dot[Transpose[g],j,h]-Dot[o,w];
 v=w+Dot[t,LinearSolve[Part[o,r,r],Part[v,r]]];
 d=Norm[v-u]/Max[Norm[v],1/1000000000000];u=v;
 {u,d,Min[h+Dot[g,u]]},{i,1,24}];
u=Part[Last[s],1];
v=h+Dot[g,u];p₁=Table[1000000*Max[0,-Part[v,i]],{i,1,Length[c]}];p₂=p₁*b;
v=Dot[k,u]-Dot[Transpose[g],p₂];
r₁=Total[Table[Part[q,i,1]*Part[v,2*i]-Part[q,i,2]*Part[v,2*i-1],{i,d₁}]];
r₂=Total[Table[(Part[q,i,1]-3)*Part[v,2*i]-Part[q,i,2]*Part[v,2*i-1],{i,d₂}]];
Labeled[Table[{Part[s,i,2],Part[s,i,3]},{i,21,24}],"last iterations: displacement change and minimum gap / rp1"]
Labeled[{r₁,r₂}*840000,"pinion and driven bore torques [N m]"]
Labeled[Norm[Part[v,r]]/Max[Norm[p₂],1/1000000000000],"relative free-DOF equilibrium residual"]
Labeled[Total[p₂]*N[210000000000*(20/1000)*(10/1000)],"total normal contact force [N]"]'''),
        text(r'''## 接触压力与应力

压力图使用接触积分权重还原压力，横坐标为接触点的高度。应力从各三角形的位移梯度计算，先按单元面积平均应力张量，再计算节点 von Mises 应力：

$$\sigma_{\mathrm{VM}}=\sqrt{\sigma_{xx}^2-\sigma_{xx}\sigma_{yy}+\sigma_{yy}^2+3\tau_{xy}^2}.$$

同时输出单元值与恢复后节点值的峰值。应力图显示原始几何，避免位移放大造成齿面视觉重叠。

整体图的色标上限取节点应力的 95% 分位值，超过上限的区域显示为红色。接触区与齿根图保留各自的色标。'''),
        calc('''Block[{a,c₁,c₂,d,d₂,g,o₁,o₂,o₃,o₄,o₅,p₃,r,s,t,v,v₁,v₂,w},
o₁=Labeled[ListLinePlot[Sort[Table[{20*Part[q,Part[c,i,1],2],210000*Part[p₁,i]},{i,1,Length[c]}]]],"normal contact pressure [MPa] versus y [mm]"];
d=Join[Part[f,1],Table[j+e,{j,Part[f,2]}]];
g={{-1,-1},{1,0},{0,1}};
s=Table[
 v=Dot[Transpose[Table[{Part[u,2*i-1],Part[u,2*i]},{i,j}]],g,Inverse[Dot[Transpose[Table[Part[q,i],{i,j}]],g]]];
 {(Part[v,1,1]+3/10*Part[v,2,2])/(1-9/100),(Part[v,2,2]+3/10*Part[v,1,1])/(1-9/100),(Part[v,1,2]+Part[v,2,1])/(2*(1+3/10))},{j,d}];
a=Table[Abs[Det[Dot[Transpose[Table[Part[q,i],{i,j}]],g]]]/2,{j,d}];
t=SparseArray[Flatten[Table[Table[{Part[d,j,i],j}->Part[a,j],{i,1,3}],{j,1,Length[d]}],1],{Length[q],Length[d]}];
v=Table[Sqrt[Part[j,1]^2+Part[j,2]^2-Part[j,1]*Part[j,2]+3*Part[j,3]^2],{j,s}];
r=Max[v];s=Dot[t,s];w=Dot[t,ConstantArray[1,Length[d]]];
s=Table[Table[Part[s,i,j]/Part[w,i],{j,1,3}],{i,1,Length[q]}];
s=Table[Sqrt[Part[j,1]^2+Part[j,2]^2-Part[j,1]*Part[j,2]+3*Part[j,3]^2],{j,s}];v=Max[s];
o₂=Labeled[{r,v}*210000,"maximum {element, recovered nodal} von Mises stress [MPa]"];
p₃=Table[{Part[q,i,1],Part[q,i,2],0},{i,1,Length[q]}];
c₁=Table[ColorData["TemperatureMap"][Part[s,i]/v],{i,1,Length[q]}];
v₁=Part[Sort[s],Ceiling[95*Length[s]/100]];
c₂=Table[ColorData["TemperatureMap"][Min[1,Part[s,i]/v₁]],{i,1,Length[q]}];
o₃=Labeled[Legended[Graphics3D[{GraphicsComplex[p₃,Polygon[d],VertexColors->c₂]}],BarLegend[{"TemperatureMap",{0,v₁*210000}},LegendLabel->"von Mises [MPa], clipped above scale"]],"plane-stress gears, undeformed geometry"];
d₂=Table[If[Abs[Part[Mean[Table[Part[q,i],{i,j}]],1]-86/100]<9/100&&Abs[Part[Mean[Table[Part[q,i],{i,j}]],2]-5/100]<18/100,j,Nothing],{j,d}];
v₂=Max[Table[Part[s,i],{i,Union[Flatten[d₂]]}]];
d=Table[If[Abs[Part[Mean[Table[Part[q,i],{i,j}]],1]-1]<1/12&&Abs[Part[Mean[Table[Part[q,i],{i,j}]],2]]<1/20,j,Nothing],{j,d}];
o₄=Labeled[Legended[Graphics3D[{GraphicsComplex[p₃,Polygon[d],VertexColors->c₁]},PlotRange->{{39/40,41/40},{-1/40,1/40},{-1,1}}],BarLegend[{"TemperatureMap",{0,v*210000}},LegendLabel->"von Mises [MPa]"]],"tooth-contact detail"];
o₅=Labeled[Legended[Graphics3D[{Table[GraphicsComplex[Table[Part[p₃,i],{i,j}],Polygon[{1,2,3}],VertexColors->Table[ColorData["TemperatureMap"][Min[1,Part[s,i]/v₂]],{i,j}]],{j,d₂}]},PlotRange->{{79/100,94/100},{-5/100,19/100},{-1,1}}],BarLegend[{"TemperatureMap",{0,v₂*210000}},LegendLabel->"von Mises [MPa]"]],"pinion root fillets, local stress scale"];
{o₁,o₂,o₃,o₄,o₅}
]''')
    ]}
