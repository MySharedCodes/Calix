"""Body-fitted quadrilateral mesh and an explicit algebraic RANS closure."""


def notebook(text,calc):
    return {'title':'机翼：稳态流场与湍流闭合','component':'pde','cells':[
    text(r'''# 机翼：稳态流场与湍流闭合

## 翼型与网格

取 NACA 0012 翼型的二维剖面。以弦长 $c$、来流速度 $U$ 和密度 $\rho$ 无量纲化，雷诺数 $Re=20000$，攻角 $\alpha=2^\circ$。假定流动不可压缩、定常且附着。

$$y=\pm0.6\left(0.2969\sqrt{x}-0.1260x-0.3516x^2+0.2843x^3-0.1036x^4\right),\qquad0\le x\le1.$$

远场边界为圆心 $(0.5,0)$、半径 6 的圆。四边形网格沿翼面闭合，径向按几何级数分布。第一个边界标记为翼面，第二个为远场。网格的节点和连接关系在下面生成。'''),
    calc('''Clear[x,y,u,v,p,n,j,k,a,b,c,d,e,f,g,h,m,r,s,η,α];
n=8;a=16*n;b=2*n+12;r=20000;α=2°;
c=Table[x=(1+Cos[N[2*Pi*j/a]])/2;
 {x,Sign[Sin[N[2*Pi*j/a]]]*3/5*(2969/10000*Sqrt[x]-126/1000*x-3516/10000*x^2+2843/10000*x^3-1036/10000*x^4)},{j,0,a-1}];
d=Table[{1/2+6*Cos[N[2*Pi*j/a]],6*Sin[N[2*Pi*j/a]]},{j,0,a-1}];
e=Join[{0},Table[N[15/10000]^((b-1-j)/(b-2)),{j,1,b-1}]];
f=N[Flatten[Table[Table[(1-Part[e,k])*Part[c,j,i]+Part[e,k]*Part[d,j,i],{i,1,2}],{k,1,b},{j,1,a}],1]];
g=Flatten[Table[{k*a+j+1,k*a+Mod[j+1,a]+1,(k+1)*a+Mod[j+1,a]+1,(k+1)*a+j+1},{k,0,b-2},{j,0,a-1}],1];
h=Join[Table[{j+1,Mod[j+1,a]+1},{j,0,a-1}],Table[{(b-1)*a+j+1,(b-1)*a+Mod[j+1,a]+1},{j,0,a-1}]];
m=ToElementMesh["Coordinates"->f,"MeshElements"->{QuadElement[g]},"BoundaryElements"->{LineElement[h,Join[ConstantArray[1,a],ConstantArray[2,a]]]}];
Labeled[{Length[f],Length[g]},"mesh nodes and quadrilaterals"]
Labeled[m["Wireframe"],"body-fitted mesh"]'''),
    text(r'''## 方程与边界条件

平均速度 $\boldsymbol u=(u,v)$ 和压力 $p$ 满足

$$\nabla\cdot\boldsymbol u=0,\qquad(\boldsymbol u\cdot\nabla)\boldsymbol u=-\nabla p+\nabla\cdot\left[2\eta\boldsymbol S\right],\qquad \boldsymbol S=\tfrac12(\nabla\boldsymbol u+\nabla\boldsymbol u^{\mathsf T}).$$

黏度取分子黏度与 Prandtl 混合长度涡黏度之和，近壁采用 van Driest 阻尼：

$$\eta=Re^{-1}+\ell_m^2\sqrt{2\boldsymbol S:\boldsymbol S},\qquad\ell_m=\min(0.41d,0.09)\left(1-e^{-y^+/26}\right),$$
$$y^+=d\sqrt{Re\sqrt{2\boldsymbol S:\boldsymbol S}}.$$

$d$ 为到翼面的距离。翼面无滑移；远场速度为 $(\cos\alpha,\sin\alpha)$，远场最右节点固定 $p=0$。代码中直接给出黏度表达式、方程和边界条件。速度采用二次、压力采用一次四边形单元。'''),
    calc('''Clear[x,y,u,v,p];
d=RegionDistance[Polygon[N[c]],{x,y}];
s=Sqrt[2*D[u[x,y],x]^2+2*D[v[x,y],y]^2+(D[u[x,y],y]+D[v[x,y],x])^2];
η=1/r+Min[41/100*d,9/100]^2*(1-Exp[-d*Sqrt[r*s]/26])^2*s;
h=FluidFlowPDEComponent[{{u[x,y],v[x,y],p[x,y]},{x,y}},Association["MassDensity"->1,"DynamicViscosity"->η]];
g=NDSolveValue[{h=={0,0,0},
 DirichletCondition[u[x,y]==0,ElementMarker==1],
 DirichletCondition[v[x,y]==0,ElementMarker==1],
 DirichletCondition[u[x,y]==Cos[α],ElementMarker==2],
 DirichletCondition[v[x,y]==Sin[α],ElementMarker==2],
 DirichletCondition[p[x,y]==0,x==13/2&&y==0]},
 {u,v,p},Element[{x,y},m]];
u=Part[g,1];v=Part[g,2];p=Part[g,3];
Labeled[{u,v,p},"velocity and pressure interpolants"]'''),
    text(r'''## 流场

速度云图中叠加流线，另绘压力系数 $C_p=2p$。翼型内部留白，流线由求得的速度场积分得到。

混合长度闭合没有独立的湍流输运方程，不预测自然转捩、失速或分离。修改首个单元的 $n$ 可细化网格；比较不同网格的翼面压力分布后，再讨论离散误差。'''),
    calc('''Labeled[Show[
 DensityPlot[Sqrt[u[x,y]^2+v[x,y]^2],{x,-3/5,2},{y,-7/10,7/10},PlotPoints->141],
 StreamPlot[{u[x,y],v[x,y]},{x,-3/5,2},{y,-7/10,7/10}]],"speed |u|/U and streamlines"]
Labeled[DensityPlot[2*p[x,y],{x,-3/5,2},{y,-7/10,7/10},PlotPoints->141],"pressure coefficient Cp"]''')
    ]}
