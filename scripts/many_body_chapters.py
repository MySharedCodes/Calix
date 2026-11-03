"""Additional planar and spatial chapters for the generated gravity notebook."""
def chapters(text,calc):
    return [
        text(r'''## 第二章：平面四体运动

        四个单位质量的质点初始位于 $(1,0),(0,1),(-1,0),(0,-1)$，各自沿逆时针切向以单位速率运动，G=1。对全部质点间的牛顿引力同时积分，观察 4 个时间单位。NBodySolve 的三组列表依次是质量、初始位置和初始速度。

        下图的轨迹与质点位置均在 z=0 平面，云图表示其周围三维空间中的引力势。色标为单位试探质量的势能 Φ=U/m_test；数值越负，颜色越暖、云图越不透明。
        '''),
        calc('''
        planarMasses={1,1,1,1};
        planarStart={{1,0},{0,1},{-1,0},{0,-1}};
        planarVelocity={{0,1},{-1,0},{0,-1},{1,0}};
        planar=NBodySolve[planarMasses,planarStart,planarVelocity,{t,0,4}];
        Labeled[NBodyPlot3D[planar,planarMasses,{t,0,4}],"four bodies, planar motion and gravitational potential; G=1"]
        '''),
        text(r'''## 第三章：三维五体运动

        五个单位质量的质点中，三个初始位于 z=0 平面的正三角形顶点，外接圆半径 1.2，沿切向以速率 0.8 运动。另两个位于 z=±1.4，分别沿 x 方向以速度 ±0.3 出发。取 G=1，计算至 t=1.2。不考虑碰撞或合并。

        每种颜色对应一个天体。曲线是整段轨迹，球体表示当前时刻的位置；Φ 的体积云图随五个天体共同变化。为了显示有限的势阱，云图使用 ε=0.12 的平滑长度，即 Φ=-Σ mᵢ/√(|r-rᵢ|²+ε²)。该平滑只用于显示，运动方程和下方总能量检验仍使用未平滑的牛顿引力。
        '''),
        calc('''
        spatialMasses={1,1,1,1,1};
        spatialStart={{1.2,0,0},{-0.6,0.6*Sqrt[3],0},{-0.6,-0.6*Sqrt[3],0},{0,0,1.4},{0,0,-1.4}};
        spatialVelocity={{0,0.8,0},{-0.4*Sqrt[3],-0.4,0},{0.4*Sqrt[3],-0.4,0},{0.3,0,0},{-0.3,0,0}};
        spatial=NBodySolve[spatialMasses,spatialStart,spatialVelocity,{t,0,1.2}];
        Labeled[NBodyPlot3D[spatial,spatialMasses,{t,0,1.2}],"five bodies, spatial motion and gravitational potential; G=1"]
        '''),
        text('### 空间五体的能量与总动量检验\n\n总能量为全部天体的动能与两两引力势能之和；它与云图中的单位试探质量势能不是同一个量。'),
        calc('''
        kineticSpatial=Total[Table[Part[spatialMasses,i]/2*Total[Table[D[Part[spatial,i,j],t]^2,{j,1,3}]],{i,1,5}]];
        potentialSpatial=-Total[Flatten[Table[Part[spatialMasses,i]*Part[spatialMasses,j]/Sqrt[Total[Table[(Part[spatial,i,k]-Part[spatial,j,k])^2,{k,1,3}]]],{i,1,4},{j,i+1,5}],1]];
        energySpatial=kineticSpatial+potentialSpatial;
        momentumSpatial=Table[Total[Table[Part[spatialMasses,i]*D[Part[spatial,i,j],t],{i,1,5}]],{j,1,3}];
        Column[{
          Labeled[Plot[energySpatial-ReplaceAll[energySpatial,t->0],{t,0,1.2}],"five-body total energy drift"],
          Labeled[Plot[momentumSpatial,{t,0,1.2},PlotLegends->{"px","py","pz"}],"five-body total momentum"]
        }]
        '''),
    ]
