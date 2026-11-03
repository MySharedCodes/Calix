"""Generate executable case notebooks from problem statements and calculation cells."""
import json
from pathlib import Path
from textwrap import dedent
from inspect import cleandoc
from example_annotations import annotate_notebook
from example_symbols import compact_notebook
from many_body_chapters import chapters
from competition_cases import notebooks as competition_notebooks
from pde_notebooks import notebooks as pde_notebooks
from conic_case import notebooks as conic_notebooks
from drag_case import notebook as drag_notebook
from hydrogen_case import notebook as hydrogen_notebook
from lattice_case import notebook as lattice_notebook

root = Path(__file__).resolve().parents[1]


def text(code):
    return {'mode': 'markdown', 'code': cleandoc(code)}


def calc(code):
    return {'mode': 'source', 'code': dedent(code).strip()}


notebooks = [
    {'title': '高考物理：2016 全国Ⅲ卷第25题最后一问', 'cells': [
        text(r'''
        # 高考物理：2016 全国Ⅲ卷第25题最后一问

        两条间距为 $l$ 的光滑水平导轨左端接电阻 $R$，导体棒与导轨电阻忽略。固定面积 $S$ 内的磁场为 $B_1=kt$；右侧磁场为 $B_0$，两者均向纸内。棒在 $t_0$ 时以速度 $v_0$ 越过右侧磁场边界，此后匀速。求 $t>t_0$ 时的总磁通量和所加恒力。取向纸内为磁通正方向。
        ## 符号输入与输出

        输入中，S 表示固定磁场区域的面积，k 是该区域磁感应强度随时间的变化率；b0、ell、v0、t0、res 分别对应 $B_0,l,v_0,t_0,R$，t 是时刻，tau 是积分变量。

        In[1] 依次输出棒进入右侧磁场后扫过的面积 sweptArea、总磁通量 flux、电动势大小 emf、电流大小 current、维持匀速所需的外力大小 force。参数取正，外力方向沿棒的运动方向。
        '''),
        calc('''
        Clear[k,S,b0,ell,v0,t0,res,t,tau];
        sweptArea=ell*Integrate[v0,{tau,t0,t}];
        flux=k*t*S+b0*sweptArea;
        emf=D[flux,t];
        current=emf/res;
        force=Simplify[b0*ell*current];
        Column[{sweptArea,flux,emf,current,force}]
        '''),
        text('## 量纲与参数计算\n\n取 $B_0=1$ T、$l=0.5$ m、$v_0=2$ m/s、$k=0.2$ T/s、$S=0.3$ m²、$R=2$ Ω、$t_0=1$ s。\n\nIn[2] 先将外力表达式的组合单位化简，再输出外力的数值（单位 N），最后绘制总磁通量随时间的曲线（横轴为秒，纵轴为 Wb）。values 将这些参数值代入符号结果。'),
        calc('''
        values={b0->1,ell->1/2,v0->2,k->1/5,S->3/10,res->2,t0->1};
        Column[{
          UnitSimplify["T^2*m^3/(s*ohm)"],
          ReplaceAll[force,values][N],
          Plot[ReplaceAll[flux,values],{t,1,4}]
        }]
        '''),
    ]},
    {'title': '高考数学：2008 江西理科第22题', 'cells': [
        text(r'''
        # 高考数学：2008 江西理科第22题

        设 $a>0,x>0$，$f(x)=1/\sqrt{1+x}+1/\sqrt{1+a}+\sqrt{ax/(ax+8)}$。

        当 $a=8$ 时求单调区间；求全部正参数范围内 $f(x)$ 的精确下确界与上确界。

        ## 固定参数时的单调性

        In[1] 取 $a=8$，依次输出导函数、正半轴上的驻点、递增区间、递减区间、驻点处函数值，以及函数图像。
        '''),
        calc('''
        Clear[a,x,p,q,u,v,gap,poly];
        f=1/Sqrt[1+x]+1/Sqrt[1+a]+Sqrt[a*x/(a*x+8)];
        f8=ReplaceAll[f,a->8];
        critical=SolveValues[D[f8,x]==0,x];
        Column[{
          Simplify[D[f8,x]],critical,
          Reduce[{D[f8,x]>0,x>0},x,Reals],Reduce[{D[f8,x]<0,x>0},x,Reals],
          Table[Simplify[ReplaceAll[f8,x->p]],{p,critical}],Plot[f8,{x,1/100,8}]
        }]
        '''),
        text(r'''## 全局解析上下界

        输出依次为精确下确界与上确界、严格界的四项代数检验。检验依次覆盖下界、上界、根式项为正、根式项小于一；每项分别检查分子和分母的系数，全部为 True 表示严格界成立。最后绘制正参数区域的函数曲面。
        '''),
        calc('''
        bounds=Sort[{Limit[ReplaceAll[f,a->x],x->0],Limit[ReplaceAll[f,a->x],x->Infinity]}];
        square=Factor[Together[ReplaceAll[(f-1/Sqrt[1+x]-1/Sqrt[1+a])^2,{x->1/u^2-1,a->1/v^2-1}]]];
        gaps={
          Together[ReplaceAll[square-(First[bounds]-u-v)^2,{u->p/(1+p+q),v->q/(1+p+q)}]],
          Together[ReplaceAll[(Last[bounds]-u-v)^2-square,{u->1-p/(1+p+q),v->1-q/(1+p+q)}]],
          Together[ReplaceAll[square,{u->p/(1+p),v->q/(1+q)}]],
          Together[ReplaceAll[1-square,{u->p/(1+p),v->q/(1+q)}]]
        };
        certificates=Table[Table[
          Min[Flatten[CoefficientList[poly,{p,q}]]]>=0&&Max[Flatten[CoefficientList[poly,{p,q}]]]>0,
          {poly,{Numerator[gap],Denominator[gap]}}],{gap,gaps}];
        Column[{
          bounds,certificates,
          Plot3D[ReplaceAll[f,{a->Exp[p],x->Exp[q]}],{p,-8,8},{q,-8,8}]
        }]
        '''),
    ]},
    {'title': 'IMO 1979 第1题：交错调和和', 'cells': [
        text(r'''
        # IMO 1979 第1题：交错调和和

        将 $1-\frac12+\frac13-\frac14+\cdots-\frac1{1318}+\frac1{1319}$ 写成既约分数 $p/q$，检验 $p$ 是否能被 $1979$ 整除。

        ## 精确有理数计算

        依次输出和的数值近似、分子和分母的十进制位数、最大公因数、分子及分母除以 1979 的余数，以及分子除以 1979 的精确商。
        '''),
        calc('''
        Clear[k,p,q];
        total=Sum[(-1)^(k+1)/k,{k,1,1319}];
        p=Numerator[total]; q=Denominator[total];
        Column[{
          N[total,30],{IntegerLength[p],IntegerLength[q]},GCD[p,q],
          {Mod[p,1979],Mod[q,1979]},p/1979
        }]
        '''),
    ]},
    {'title': 'IMO 1978 第1题：幂的末三位', 'cells': [
        text(r'''
        # IMO 1978 第1题：幂的末三位

        求正整数 $m<n$，使 $1978^m$ 与 $1978^n$ 的十进制末三位相同，并使 $m+n$ 最小。

        ## 模幂与整数搜索

        枚举 $1\le m<n\le120$。输出最小和、对应的指数对及末三位、搜索范围是否覆盖全部更小的和，并绘制模幂序列。
        '''),
        calc('''
        Clear[m,n,row];
        bound=120;
        residues=Table[PowerMod[1978,n,1000],{n,1,bound}];
        pairs=Flatten[Table[If[Part[residues,m]==Part[residues,n],{m,n},Nothing],{n,2,bound},{m,1,n-1}],1];
        best=Min[Table[Total[row],{row,pairs}]];
        winners=Table[If[Total[row]==best,Join[row,{Part[residues,First[row]]}],Nothing],{row,pairs}];
        Column[{
          best,winners,best<bound+1,
          ListPlot[Table[{n,Part[residues,n]},{n,1,bound}]]
        }]
        '''),
    ]},
    {'title': '弹性双摆：两段弹簧与两个小球', 'cells': [
        text(r'''
        # 弹性双摆：两段弹簧与两个小球

        固定点、第一球、第二球依次由两段无质量弹簧连接。两球质量均为 $1$ kg，弹簧刚度均为 $40$ N/m，原长均为 $1$ m，$g=9.81$ m/s²。取竖直向下为 $y$ 正方向，不计阻尼和空气阻力。

        分别计算小振幅线性模型和大振幅完整非线性模型。两种情况均静止释放。

        ## 平衡位置与线性化
        '''),
        calc('''
        Clear[x1,y1,x2,y2,h1,h2,u1,u2,t,tau,i,j,u];
        mass=1; spring=40; length=1; gravity=981/100;
        heights=First[SolveValues[{spring*(h1-length)==2*mass*gravity,spring*(h2-length)==mass*gravity},{h1,h2}]];
        rest={0,Part[heights,1],0,Total[heights]};
        coords={x1,y1,x2,y2};
        potential=spring/2*(Sqrt[x1^2+y1^2]-length)^2+spring/2*(Sqrt[(x2-x1)^2+(y2-y1)^2]-length)^2-mass*gravity*(y1+y2);
        force=Table[-D[potential,Part[coords,i]]/mass,{i,1,4}];
        atRest={x1->Part[rest,1],y1->Part[rest,2],x2->Part[rest,3],y2->Part[rest,4]};
        stiffness=Simplify[Table[ReplaceAll[D[potential,Part[coords,i],Part[coords,j]]/mass,atRest],{i,1,4},{j,1,4}]];
        Column[{rest,stiffness,Eigenvalues[stiffness]}]
        '''),
        text('## 小振幅解析解\n\n两球从竖直平衡位置分别向右偏移 $0.05$ m、$0.12$ m。'),
        calc('''
        small=DSolveValue[{
          u1''[t]==-Part[stiffness,1,1]*u1[t]-Part[stiffness,1,3]*u2[t],
          u2''[t]==-Part[stiffness,3,1]*u1[t]-Part[stiffness,3,3]*u2[t],
          u1[0]==1/20,u2[0]==3/25,u1'[0]==0,u2'[0]==0
        },{u1[t],u2[t]},t];
        Column[{Labeled[Part[small,1],"displacement, first ball"],Labeled[Part[small,2],"displacement, second ball"]}]
        '''),
        text('## 大振幅数值解\n\n第一段弹簧相对向下竖直方向偏转 $60°$，第二段偏转 $-45°$，初始长度取悬挂平衡长度，初速度为零。完整非线性方程使用数值积分。'),
        calc('''
        functions={x1[t],y1[t],x2[t],y2[t]};
        toFunctions={x1->x1[t],y1->y1[t],x2->x2[t],y2->y2[t]};
        equations=Table[D[Part[functions,i],{t,2}]==ReplaceAll[Part[force,i],toFunctions],{i,1,4}];
        angle1=60°; angle2=-45°;
        start={Part[heights,1]*Sin[angle1],Part[heights,1]*Cos[angle1],Part[heights,1]*Sin[angle1]+Part[heights,2]*Sin[angle2],Part[heights,1]*Cos[angle1]+Part[heights,2]*Cos[angle2]};
        initial=Flatten[Table[{ReplaceAll[Part[functions,i],t->0]==Part[start,i],ReplaceAll[D[Part[functions,i],t],t->0]==0},{i,1,4}],1];
        motion=NDSolveValue[Join[equations,initial],{x1[t],y1[t],x2[t],y2[t]},{t,0,6}]
        '''),
        text('## 位移与能量'),
        calc('''
        energy=ReplaceAll[potential,{x1->Part[motion,1],y1->Part[motion,2],x2->Part[motion,3],y2->Part[motion,4]}]+mass/2*Total[Table[D[Part[motion,i],t]^2,{i,1,4}]];
        Column[{
          Plot[small,{t,0,6},PlotLegends->{"第一球","第二球"}],
          Plot[{Part[motion,1],Part[motion,3]},{t,0,6},PlotLegends->{"第一球","第二球"}],
          Plot[energy-ReplaceAll[energy,t->0],{t,0,6}]
        }]
        '''),
        text('## 大振幅运动动画'),
        calc('''
        spring1=Table[{u*Part[motion,1]+Sin[12*Pi*u]/30,-u*Part[motion,2]},{u,0,1,1/30}];
        spring2=Table[{(1-u)*Part[motion,1]+u*Part[motion,3]+Sin[12*Pi*u]/30,-(1-u)*Part[motion,2]-u*Part[motion,4]},{u,0,1,1/30}];
        Animate[Graphics[{
          Line[ReplaceAll[spring1,t->tau]],Line[ReplaceAll[spring2,t->tau]],
          Point[ReplaceAll[{{Part[motion,1],-Part[motion,2]},{Part[motion,3],-Part[motion,4]}},t->tau]]
        }],{tau,0,6}]
        '''),
    ]},
    {'title': '五球弹簧串：松手下落', 'cells': [
        text(r'''
        # 五球弹簧串：松手下落

        五个质量均为 $1$ kg 的小球由四段无质量弹簧串联，弹簧刚度均为 $100$ N/m，原长均为 $1$ m。握住最上方小球，使整串竖直静止，随后松手。取竖直向下为正方向，最上方小球初始位置为 $0$，$g=9.81$ m/s²。不计空气阻力、弹簧质量和小球碰撞。

        求五球的解析运动、初始加速度及质心运动，观察松手后 $5$ s 内的运动。

        ## 悬挂平衡位置
        '''),
        calc('''
        Clear[a1,a2,a3,a4,a5,y1,y2,y3,y4,y5,t,tau,i,u];
        mass=1; spring=100; length=1; gravity=981/100; duration=5;
        rest=First[SolveValues[{
          a1==0,
          0==mass*gravity+spring*(a3-2*a2+a1),
          0==mass*gravity+spring*(a4-2*a3+a2),
          0==mass*gravity+spring*(a5-2*a4+a3),
          0==mass*gravity-spring*(a5-a4-length)
        },{a1,a2,a3,a4,a5}]];
        rest
        '''),
        text('## 五球解析解'),
        calc('''
        functions={y1[t],y2[t],y3[t],y4[t],y5[t]};
        equations={
          y1''[t]==gravity+spring/mass*(y2[t]-y1[t]-length),
          y2''[t]==gravity+spring/mass*(y3[t]-2*y2[t]+y1[t]),
          y3''[t]==gravity+spring/mass*(y4[t]-2*y3[t]+y2[t]),
          y4''[t]==gravity+spring/mass*(y5[t]-2*y4[t]+y3[t]),
          y5''[t]==gravity-spring/mass*(y5[t]-y4[t]-length)
        };
        initial=Flatten[Table[{ReplaceAll[Part[functions,i],t->0]==Part[rest,i],ReplaceAll[D[Part[functions,i],t],t->0]==0},{i,1,5}],1];
        motion=DSolveValue[Join[equations,initial],{y1[t],y2[t],y3[t],y4[t],y5[t]},t];
        Column[{Labeled[Part[motion,1],"position, ball 1"],Labeled[Part[motion,2],"position, ball 2"],Labeled[Part[motion,3],"position, ball 3"],Labeled[Part[motion,4],"position, ball 4"],Labeled[Part[motion,5],"position, ball 5"]}]
        '''),
        text('## 松手后的初始运动'),
        calc('''
        center=Simplify[Total[motion]/5];
        Column[{
          Simplify[Table[ReplaceAll[D[Part[motion,i],{t,2}],t->0],{i,1,5}]],
          center,
          Series[Part[motion,5],{t,0,10}]
        }]
        '''),
        text('## 底部两球与自由落体的位移对比\n\n向下位移均从各自的初始位置计起。第一张图依次绘制最下方小球、倒数第二个小球和从静止开始的自由落体；第二张图绘制这两个小球相对自由落体的位移差。时间范围为 0 至 5 s，并画出自由落体对应的零基线。'),
        calc('''
        bottom=Part[motion,5]-Part[rest,5];
        nextBottom=Part[motion,4]-Part[rest,4];
        freeFall=gravity*t^2/2;
        Column[{
          Plot[{bottom,nextBottom,freeFall},{t,0,duration},PlotLegends->{"最下方小球","倒数第二个小球","自由落体"}],
          Plot[{bottom-freeFall,nextBottom-freeFall,0},{t,0,duration},PlotLegends->{"底球相对自由落体","次底球相对自由落体","自由落体（零基线）"}]
        }]
        '''),
        text('## 下落动画\n\n视角随质心下落，纵坐标表示相对质心的位置。'),
        calc('''
        relative=Table[Simplify[Part[motion,i]-center],{i,1,5}];
        coils=Table[Table[{3/25*Sin[12*Pi*u],-(1-u)*Part[relative,i]-u*Part[relative,i+1]},{u,0,1,1/24}],{i,1,4}];
        balls=Table[{0,-Part[relative,i]},{i,1,5}];
        Animate[Graphics[{
          Line[ReplaceAll[Part[coils,1],t->tau]],Line[ReplaceAll[Part[coils,2],t->tau]],
          Line[ReplaceAll[Part[coils,3],t->tau]],Line[ReplaceAll[Part[coils,4],t->tau]],
          Point[ReplaceAll[balls,t->tau]]
        }],{tau,0,duration}]
        '''),
    ]},
    {'title': '多天体：平面与三维引力运动', 'cells': [
        text(r'''
        # 多天体：平面与三维引力运动

        ## 第一章：平面三体运动

        三个单位质量的质点在同一平面内相互吸引，取无量纲引力常数 $G=1$。不计碰撞及其他作用力。初始位置依次为 $(-0.97000436,0.24308753)$、$(0.97000436,-0.24308753)$、$(0,0)$；初始速度依次为 $(0.466203685,0.43236573)$、$(0.466203685,0.43236573)$、$(-0.93240737,-0.86473146)$。

        计算 $0\le t\le6.3259$ 内的运动，绘制引力势分布并检查能量、总动量和角动量。

        ## 引力方程与数值解
        '''),
        calc('''
        Clear[x1,y1,x2,y2,x3,y3,x,y,t,tau,i,j,u];
        coords={x1,y1,x2,y2,x3,y3};
        potential=-1/Sqrt[(x1-x2)^2+(y1-y2)^2]-1/Sqrt[(x1-x3)^2+(y1-y3)^2]-1/Sqrt[(x2-x3)^2+(y2-y3)^2];
        functions={x1[t],y1[t],x2[t],y2[t],x3[t],y3[t]};
        rules={x1->x1[t],y1->y1[t],x2->x2[t],y2->y2[t],x3->x3[t],y3->y3[t]};
        equations=Table[D[Part[functions,i],{t,2}]==ReplaceAll[-D[potential,Part[coords,i]],rules],{i,1,6}];
        positions={-0.97000436,0.24308753,0.97000436,-0.24308753,0,0};
        velocities={0.466203685,0.43236573,0.466203685,0.43236573,-0.93240737,-0.86473146};
        initial=Flatten[Table[{ReplaceAll[Part[functions,i],t->0]==Part[positions,i],ReplaceAll[D[Part[functions,i],t],t->0]==Part[velocities,i]},{i,1,6}],1];
        motion=NDSolveValue[Join[equations,initial],{x1[t],y1[t],x2[t],y2[t],x3[t],y3[t]},{t,0,6.3259}]
        '''),
        text('## 守恒量检查\n\n依次绘制总能量误差、总动量的两个分量、角动量。'),
        calc('''
        energy=ReplaceAll[potential,{x1->Part[motion,1],y1->Part[motion,2],x2->Part[motion,3],y2->Part[motion,4],x3->Part[motion,5],y3->Part[motion,6]}]+Total[Table[D[Part[motion,i],t]^2/2,{i,1,6}]];
        momentum={Total[Table[D[Part[motion,2*i-1],t],{i,1,3}]],Total[Table[D[Part[motion,2*i],t],{i,1,3}]]};
        angular=Total[Table[Part[motion,2*i-1]*D[Part[motion,2*i],t]-Part[motion,2*i]*D[Part[motion,2*i-1],t],{i,1,3}]];
        Column[{
          Plot[energy-ReplaceAll[energy,t->0],{t,0,6.3259}],
          Plot[momentum,{t,0,6.3259},PlotLegends->{"水平总动量","竖直总动量"}],Plot[angular,{t,0,6.3259}]
        }]
        '''),
        text(r'''## 三维引力势分布

        横向两个坐标表示平面位置，曲面高度表示单位质量的引力势。三个势阱随天体运动。显示时取平滑尺度 $\epsilon=0.15$，使质点中心的势阱保持有限；该平滑仅用于绘图，不改变前面的引力运动方程。竖直显示比例取水平的一半。
        '''),
        calc('''
        epsilon=3/20;
        field=-Total[Table[1/Sqrt[(x-Part[motion,2*i-1])^2+(y-Part[motion,2*i])^2+epsilon^2],{i,1,3}]];
        Animate[Plot3D[ReplaceAll[field,t->tau],{x,-2,2},{y,-3/2,3/2},PlotPoints->41,BoxRatios->{1,1,1/2}],{tau,0,6.3259}]
        '''),
    ]},
]

notebooks.extend([
    {'title': '电流线圈附近的带电粒子', 'cells': [
        text(r'''
        # 电流线圈附近的带电粒子

        三个同轴细圆线圈半径均为 $R=0.1$ m，中心位于 $z/R=-0.7,0,0.7$，电流均为 $I=1000$ A，从 $+z$ 看为逆时针。六个质点质量相同，前三个带 $+e$、后三个带 $-e$ 电荷；质量均取质子质量。不计质点间相互作用、重力、辐射及对线圈的反作用。真空磁导率取 $4\pi\times10^{-7}$ H/m。

        以线圈半径为长度单位、三线圈在原点的合磁场 $B_0$ 为磁场单位、$m_p/(eB_0)$ 为时间单位。六个不同的初始位置与速度在计算单元的 starts、velocities 中列出；各行与编号一一对应。计算至无量纲时间 20。理想导线不属于粒子可通过的区域。

        ## 轴线磁场

        依次输出轴线磁场、中心磁场、时间单位和速度单位。
        '''),
        calc('''
        Clear[z,phi,x,y,t,i,j,h,row,sign];
        coils={-0.7,0,0.7};
        normalization=Total[Table[1/(1+h^2)^(3/2),{h,coils}]];
        axis=Total[Table[1/(1+(z-h)^2)^(3/2),{h,coils}]]/normalization;
        radius=0.1[m]; current=1000[A]; mu=4*Pi*1e-7[H/m];
        charge=1.602176634e-19[C]; mass=1.67262192369e-27[kg];
        center=mu*current/(2*radius)*normalization;
        timeScale=mass/(charge*center);
        Column[{axis,N[UnitConvert[center,"mT"],12],N[UnitConvert[timeScale,"us"],12],N[UnitConvert[radius/timeScale,"km/s"],12]}]
        '''),
        text('## 中心均匀场近似的解析运动\n\n此处将磁场固定为中心值；解析轨迹用来对照后面的非均匀磁场计算。'),
        calc('''
        uniform=DSolveValue[{
          x''[t]==y'[t],y''[t]==-x'[t],z''[t]==0,
          x[0]==11/50,y[0]==0,z[0]==1/10,x'[0]==0,y'[0]==4/25,z'[0]==2/25
        },{x[t],y[t],z[t]},t];
        Column[{Labeled[Part[uniform,1],"uniform field, x(t)"],Labeled[Part[uniform,2],"uniform field, y(t)"],Labeled[Part[uniform,3],"uniform field, z(t)"]}]
        '''),
        text('## 非均匀磁场中的运动\n\n每个圆线圈的磁场采用完全椭圆积分解析式，EllipticK 和 EllipticE 的自变量为参数 m。将三个平移后的磁场相加，分别求解六个质点的洛伦兹运动方程。'),
        calc('''
        rho=Sqrt[x^2+y^2];
        distance=Sqrt[(1+rho)^2+z^2]; delta=(1-rho)^2+z^2;
        parameter=4*rho/distance^2;
        radial=z/(Pi*rho*distance)*(-EllipticK[parameter]+(1+rho^2+z^2)/delta*EllipticE[parameter]);
        axial=1/(Pi*distance)*(EllipticK[parameter]+(1-rho^2-z^2)/delta*EllipticE[parameter]);
        singleField={radial*x/rho,radial*y/rho,axial};
        contributions=Table[ReplaceAll[singleField,z->z-h],{h,coils}];
        field=Table[Total[Table[Part[row,j],{row,contributions}]]/normalization,{j,1,3}];
        rules={x->x[t],y->y[t],z->z[t]};
        magnetic=ReplaceAll[field,rules];
        signs={1,1,1,-1,-1,-1};
        starts={{0.22,0,0.1},{-0.28,0.12,-0.15},{0.15,-0.3,0.25},{-0.22,-0.1,0.12},{0.3,0.18,-0.2},{-0.12,0.32,0.28}};
        velocities={{0,0.16,0.08},{0.14,0.04,0.07},{-0.12,0.1,-0.08},{0.08,-0.14,0.06},{-0.1,0.12,-0.07},{0.15,-0.06,-0.09}};
        motions=Table[NDSolveValue[{
          x''[t]==Part[signs,k]*(y'[t]*Part[magnetic,3]-z'[t]*Part[magnetic,2]),
          y''[t]==Part[signs,k]*(z'[t]*Part[magnetic,1]-x'[t]*Part[magnetic,3]),
          z''[t]==Part[signs,k]*(x'[t]*Part[magnetic,2]-y'[t]*Part[magnetic,1]),
          x[0]==Part[starts,k,1],y[0]==Part[starts,k,2],z[0]==Part[starts,k,3],
          x'[0]==Part[velocities,k,1],y'[0]==Part[velocities,k,2],z'[0]==Part[velocities,k,3]
        },{x[t],y[t],z[t]},{t,0,20}],{k,1,6}];
        Labeled[motions,"six particles, position functions {x,y,z}/R"]
        '''),
        text('## 磁场与轨迹\n\n铜色圆环为三个线圈，浅灰青色细线为合磁场的磁感线；磁感线由 d r/ds=B/|B| 数值积分得到。六条彩色粗线对应六个质点。两张过轴半透明切片以颜色表示 |B|/B₀，采用 log(1+|B|/B₀) 色标，超过色标上限的强场按上限显示。理想导线周围 0.075R 的区域不作场强显示。'),
        calc('''
        Labeled[MagneticFieldPlot3D[field,{x,y,z},coils,motions,signs,{t,0,20}],"three coils, dense field lines and six charged particles; coordinates / R"]
        '''),
        text('## 高度与能量\n\n磁力不做功。均匀场近似对应第1个粒子的初始条件；高度图同时显示六个粒子。再分别检查六条数值轨迹的速度平方漂移。'),
        calc('''
        heights=Table[Part[motions,k,3],{k,1,6}];
        speeds2=Table[Total[Table[D[Part[motions,k,i],t]^2,{i,1,3}]],{k,1,6}];
        speedDrifts=Table[Part[speeds2,k]-ReplaceAll[Part[speeds2,k],t->0],{k,1,6}];
        Column[{
          Labeled[Plot[Join[{Part[uniform,3]},heights],{t,0,20},PlotLegends->{"uniform, 1","1,+e","2,+e","3,+e","4,-e","5,-e","6,-e"}],"height, z/R"],
          Labeled[Plot[speedDrifts,{t,0,20},PlotLegends->{"1,+e","2,+e","3,+e","4,-e","5,-e","6,-e"}],"speed squared drift, six particles"]
        }]
        '''),
    ]},
    hydrogen_notebook(text, calc),
])

next(n for n in notebooks if n['title'].startswith('多天体'))['cells'].extend(chapters(text,calc))
notebooks.extend(competition_notebooks(text, calc))
notebooks.extend(pde_notebooks(text, calc))
notebooks.extend(conic_notebooks(text, calc))
notebooks.append(lattice_notebook(text,calc))
target = root / 'frontend/src/example-notebooks.json'
prepared=[]
for notebook in notebooks:
    if notebook.get('component')=='pde' or notebook['title'].startswith(('高考数学：2022','类氢离子','格点色动力学')):
        for cell in notebook['cells']:
            if cell['mode']=='markdown':
                cell['code']=cell['code'].replace('$$','\n$$\n')
        prepared.append(annotate_notebook(notebook))
    else:
        prepared.append(compact_notebook(annotate_notebook(notebook)))
target.write_text(json.dumps(prepared, ensure_ascii=False, indent=2), encoding='utf-8')
starter_path = root / 'frontend/src/starter.json'
starter = drag_notebook(text, calc)
for cell in starter['cells']:
    if cell['mode']=='markdown':
        cell['code']=cell['code'].replace('$$','\n$$\n')
starter_path.write_text(json.dumps(annotate_notebook(starter), ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Created {len(notebooks)} case notebooks')
