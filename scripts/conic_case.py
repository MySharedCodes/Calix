"""Independent conic case; no solver or application changes."""


def notebooks(text, calc):
    return [{
        'title': '高考数学：2022 全国乙卷理科第20题',
        'cells': [
            text(r'''# 高考数学：2022 全国乙卷理科第20题

椭圆 E 的中心为原点，对称轴为坐标轴，经过 A(0,-2)、B(3/2,-1)。求椭圆方程。过 P(1,-2) 的直线与 E 交于不同的 M、N；过 M 作水平线，与直线 AB 交于 T，令向量 MT=TH，证明 HN 经过定点。

以下以直线 AB 承载代数计算；若要求 T 位于线段 AB，再筛选相应构型，恒等式仍成立。排除重合交点及 H=N 等无法定义直线的退化情形。

## 椭圆与交点

依次输出椭圆方程、联立后的二次式、判别式、两不同实交点所需的斜率范围。
'''),
            calc('''Clear[x,y,k,u,v,z,e,q,c₁,d,r,p₁,p₂,y₁,y₂,h,s,a,b,c,f,j,t];
z=First[SolveValues[{4*v==1,9*u/4+v==1},{u,v}]];
e=Part[z,1]*x^2+Part[z,2]*y^2;
Labeled[e==1,"ellipse equation"]
q=Expand[4*x^2+3*(k*x-k-2)^2-12];
Labeled[q,"intersection polynomial"]
c₁=CoefficientList[q,x];
d=Factor[Part[c₁,2]^2-4*Part[c₁,3]*Part[c₁,1]];
Labeled[d,"secant discriminant"]
Labeled[Reduce[d>0,k,Reals],"slopes giving two distinct intersections"]'''),
            text('''## 非竖直割线的定点验证

代码求 M、N，构造 T 与 H，以行列式验证 A、H、N 共线；最后四项为 M、N 在椭圆上、MT=TH、A 在 HN 上的精确残差，应全部为零。'''),
            calc('''r=SolveValues[q==0,x];
p₁=First[r]; p₂=Last[r];
y₁=k*p₁-k-2; y₂=k*p₂-k-2;
h=3*y₁+6-p₁;
Labeled[{p₁,y₁},"M coordinates"]
Labeled[{p₂,y₂},"N coordinates"]
Labeled[{h,y₁},"H coordinates"]
Labeled[Simplify[{p₁^2/3+y₁^2/4-1,p₂^2/3+y₂^2/4-1,
  h+p₁-2*(3*y₁/2+3),
  (h-p₂)*(-2-y₂)-(y₁-y₂)*(0-p₂)}],"ellipse, midpoint and fixed-point residuals"]'''),
            text('''## 竖直割线与退化情形

取 x=1，交换上下两个交点分别检验，不遗漏斜率不存在的割线。输出两个共线残差和定点。斜率边界对应切线，不能作为两个不同交点使用。'''),
            calc('''s=SolveValues[1/3+y^2/4==1,y];
Labeled[Simplify[Table[(3*j+4)*(-2+j)-2*j*(-1),{j,s}]],"vertical secant collinearity residuals"]
Labeled[{0,-2},"fixed point A"]'''),
            text('''## 一个有效构型

选 k=-3，分别显示 M、N、T、H，并验证 T 在线段 AB 内。图中显示椭圆、割线和 HN；定点为 A(0,-2)。'''),
            calc('''a=ReplaceAll[p₂,k->-3]; b=ReplaceAll[p₁,k->-3];
c=ReplaceAll[y₂,k->-3]; f=ReplaceAll[y₁,k->-3];
j=Simplify[3*c+6-a];
Labeled[N[{{a,c},{b,f},{3*c/2+3,c},{j,c}},8],"M, N, T, H coordinates"]
Labeled[Simplify[-2<=c&&c<=-1],"T lies on segment AB"]
Labeled[Show[Plot[{-3*x+1,Simplify[(c-f)*(x-b)/(j-b)+f]},
 {x,-2,2},PlotRange->{-5/2,5/2},PlotLegends->{"MN","HN"}],
 ParametricPlot[{Sqrt[3]*Cos[t],2*Sin[t]},{t,0,2*Pi}]],"ellipse, secant MN and fixed-point line HN"]'''),
        ],
    }]
