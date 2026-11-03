"""Competition cases with the algebra and exhaustive search in calculation cells."""


def notebooks(text, calc):
    return [
        {'title': 'IMO 1981 第3题：整数约束下的最大值', 'cells': [
            text(r'''# IMO 1981 第3题：整数约束下的最大值

            整数 m、n 均属于 {1,2,…,1981}，且 $(n^2-mn-m^2)^2=1$。求 $m^3+n^3$ 的最大值。

            ## 求候选值并完整枚举

            先让 Calix 解出约束方程中的 n，再逐一检查全部 1981 个 m 和约束右侧的两种符号。输出全部可行整数对、目标函数的最大值及达到最大值的整数对。下方的点图显示所有可行解。
            '''),
            calc('''
            Clear[m,n,sign,candidate,row];
            branches=SolveValues[n^2-m*n-m^2==sign,n];
            pairs=Flatten[Table[
              candidate=(m+Sqrt[5*m^2+4*sign])/2;
              If[IntegerQ[candidate] && candidate>=1 && candidate<=1981,{m,candidate},Nothing],
              {m,1,1981},{sign,{-1,1}}
            ],1];
            scores=Table[Part[row,1]^3+Part[row,2]^3,{row,pairs}];
            best=Max[scores];
            winners=Table[If[Part[row,1]^3+Part[row,2]^3==best,row,Nothing],{row,pairs}];
            Column[{
              Labeled[branches,"n(m), two algebraic roots"],
              Labeled[pairs,"all feasible integer pairs {m,n}, 1...1981"],
              Labeled[best,"maximum m^3+n^3"],
              Labeled[winners,"maximizing integer pairs {m,n}"],
              Labeled[ListPlot[pairs],"all feasible pairs, horizontal m and vertical n"]
            }]
            '''),
            text('## 检查原约束与搜索范围\n\n将所有候选对代回原题约束，并检查坐标范围。枚举对每个 m 检查了两个可能的正根；另一个代数根不大于零，不属于题设范围。'),
            calc('''
            residuals=Table[(Part[row,2]^2-Part[row,1]*Part[row,2]-Part[row,1]^2)^2-1,{row,pairs}];
            Column[{
              Labeled[residuals,"original constraint residuals, all zero"],
              Labeled[{Min[Flatten[pairs]],Max[Flatten[pairs]]},"smallest and largest coordinates in the feasible set"],
              Labeled[1981*2,"number of exact candidate checks"]
            }]
            '''),
        ]},
        {'title': 'IPhO 2011 第3题：离子散射与俘获截面', 'cells': [
            text(r'''# IPhO 2011 第3题：离子散射与俘获截面

            质量 m、电荷 Q 的离子，以非相对论初速度 v₀ 从远处接近一个中性原子，碰撞参数为 b。原子质量远大于 m，位置视为固定；其电极化率为 α，诱导偶极矩满足 p=αE。忽略辐射损失。

            求偶极矩轴线上的电场、离子受到的力、相互作用势能、散射时的最近距离，以及发生电荷交换俘获的截面积。α、m、v₀、真空介电常数 ε₀ 均为正；Q 可正可负。

            ## 偶极场、力与相互作用势

            以相距 2a、电荷为 ±q 的电荷对表示偶极子，令 p=2aq。计算轴线电场的极限，将诱导偶极矩代入，再对力积分。radialForce 的负号表示吸引。最后检查 Q 反号时力是否改变。
            '''),
            calc('''
            Clear[r,a,p,Q,alpha,eps,mass,v0,b,w];
            dipoleField=Limit[p/(2*a)/(4*Pi*eps)*(1/(r-a)^2-1/(r+a)^2),a->0];
            ionField=Q/(4*Pi*eps*r^2);
            induced=alpha*ionField;
            radialForce=Simplify[-Q*ReplaceAll[dipoleField,p->induced]];
            potential=Integrate[-radialForce,r];
            c4=Simplify[-potential*r^4];
            Column[{
              Labeled[dipoleField,"dipole axial electric field"],
              Labeled[radialForce,"radial force on ion"],
              Labeled[potential,"interaction potential, zero at infinity"],
              Labeled[Simplify[ReplaceAll[radialForce,Q->-Q]-radialForce],"force change under Q -> -Q"]
            }]
            '''),
            text('## 最近距离与俘获截面\n\n用远处的初始速度、碰撞参数确定能量和角动量。将径向速度为零的条件交给 Calix 解方程；散射取较大的正半径。再求转向点合并时的碰撞参数 b₀，以及 πb₀²。b>b₀ 对应散射，b<b₀ 对应模型中的俘获；b=b₀ 为临界情形。'),
            calc('''
            energy=mass*v0^2/2;
            angularMomentum=mass*v0*b;
            effective=angularMomentum^2/(2*mass*r^2)+potential;
            turningEquation=Expand[ReplaceAll[(energy-effective)*r^4,r->Sqrt[w]]];
            turning=SolveValues[turningEquation==0,w];
            closest=Sqrt[Last[turning]];
            discriminant=Simplify[b^4-8*c4/(mass*v0^2)];
            criticalFourth=First[SolveValues[ReplaceAll[discriminant,b^4->w]==0,w]];
            critical=criticalFourth^(1/4);
            crossSection=Pi*Sqrt[criticalFourth];
            Column[{
              Labeled[effective,"effective radial potential"],
              Labeled[turning,"turning radii squared, inner and outer roots"],
              Labeled[closest,"closest approach for scattering, b > b0"],
              Labeled[critical,"critical impact parameter b0"],
              Labeled[crossSection,"charge-exchange capture cross section, pi b0^2"],
              Labeled[Simplify[ReplaceAll[turningEquation,w->Last[turning]]],"outer turning-point equation residual"]
            }]
            '''),
            text('## 有效势与最近距离\n\n为比较曲线，下面另取无量纲参数 m=v₀=1、C₄=1/2，其中 C₄ 是前面计算的吸引势系数。三条有效势曲线分别对应 b=1、b=b₀ 和 b=2；水平线为入射能量。最近距离曲线只画散射区域。此图使用的无量纲参数不代表额外的实验数据。'),
            calc('''
            normalized=b^2/(2*r^2)-1/(2*r^4);
            b0=Sqrt[2];
            normalizedClosest=Sqrt[(b^2+Sqrt[b^4-4])/2];
            Column[{
              Labeled[Plot[{ReplaceAll[normalized,b->1],ReplaceAll[normalized,b->b0],ReplaceAll[normalized,b->2],1/2},{r,0.5,4},PlotRange->{-1,2},PlotLegends->{"b=1","b=b0","b=2","incident energy"}],"dimensionless effective radial potentials"],
              Labeled[Plot[normalizedClosest,{b,b0,4}],"closest approach versus impact parameter, scattering branch"],
              Labeled[{b0,Pi*b0^2},"dimensionless {critical impact parameter,capture cross section}"]
            }]
            '''),
        ]},
    ]
