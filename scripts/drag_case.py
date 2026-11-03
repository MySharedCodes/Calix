"""Calibrate two drag laws from an observed angular maximum range."""


def notebook(text,calc):
    return {'title':'空气阻力下的二维抛体运动','cells':[
      text(r'''# 空气阻力下的二维抛体运动

      小明从平地上抛出一块质量为 $650\,\mathrm{gr}$ 的石头，初速度为 $890\,\mathrm{m/s}$。改变投射角，测得最大射程为 $7\,\mathrm{km}$。将石头视为质点，落地点与出发点等高，重力加速度取 $9.81\,\mathrm{m/s^2}$。

      分别用线性阻力和速度平方阻力拟合最大射程，求阻力系数、最佳投射角和飞行时间。取 $x$ 水平向前、$y$ 竖直向上。

      忽略风、地球曲率和空气密度变化，阻力系数取常数。
      '''),
      calc('''Clear[m,v,g,R,b,c,k,t,θ,u,r,p,q];
      m=650[gr];v=890[m/s];g=9.81[m/s^2];R=7[km];
      Labeled[m,"stone mass, grain"]
      Labeled[v,"initial speed"]
      Labeled[R,"observed maximum range"]'''),
      text(r'''## 第一部分：线性空气阻力（解析解）

      阻力为 $\boldsymbol F_\mathrm d=-b\boldsymbol v$，运动方程为

      $$m\dot v_x=-bv_x,\qquad m\dot v_y=-mg-bv_y,\qquad
      (v_x(0),v_y(0))=v_0(\cos\theta,\sin\theta).$$

      对每个 $b$ 求最大射程，再用 NSolve 确定使最大射程等于 $7\,\mathrm{km}$ 的系数。代码以 $k\,[\mathrm{kg/s}]$ 表示 $b$。
      '''),
      calc('''p=NSolve[ProjectileMaxRange[k*1[kg/s],m,v,g,"Linear"]==R,{k,0,1/10}];
      b=ReplaceAll[k,First[p]]*1[kg/s];
      q=ProjectileOptimum[b,m,v,g,"Linear"];
      Labeled[b,"linear drag coefficient b"]
      Labeled[q,"linear drag: {maximum range, optimal angle, landing time}"]
      Labeled[UnitConvert[Part[q,1]-R,"m"],"maximum-range calibration residual"]'''),
      text(r'''### 速度、位移与时间曲线

      最佳角度记作 $\theta$，令 $\beta=b/m$，线性模型的速度解析式为

      $$v_x=v_0\cos\theta\,e^{-\beta t},\qquad
      v_y=(v_0\sin\theta+g/\beta)e^{-\beta t}-g/\beta.$$

      将速度积分得到位移，计算到落地时刻。
      '''),
      calc('''θ=Part[q,2];
      u=ProjectileVelocity[b,m,v,g,θ,{t,0[s],Part[q,3]},"Linear"];
      r=Integrate[u,{t,0[s],t*1[s]}];
      Labeled[u,"linear drag velocity, {vx,vy}"]
      Labeled[r,"linear drag displacement, {x,y}"]
      Labeled[Plot[Part[r,1],{t,0[s],Part[q,3]}],"linear drag horizontal displacement versus time"]
      Labeled[Plot[Part[r,2],{t,0[s],Part[q,3]}],"linear drag vertical displacement versus time"]'''),
      calc('Labeled[Animate[ParametricPlot[r,{t,0[s],Part[q,3]}]],"linear drag flight to landing"]'),
      text(r'''## 第二部分：普通空气阻力（数值解）

      采用速度平方阻力 $\boldsymbol F_\mathrm d=-c|\boldsymbol v|\boldsymbol v$：

      $$m\dot v_x=-c\sqrt{v_x^2+v_y^2}\,v_x,\qquad
      m\dot v_y=-mg-c\sqrt{v_x^2+v_y^2}\,v_y.$$

      数值积分这组方程，搜索最佳投射角，再用 NSolve 匹配最大射程。此时 $c=k\,[\mathrm{kg/m}]$。
      '''),
      calc('''p=NSolve[ProjectileMaxRange[k*1[kg/m],m,v,g,"Quadratic"]==R,{k,0,1/1000}];
      c=ReplaceAll[k,First[p]]*1[kg/m];
      q=ProjectileOptimum[c,m,v,g,"Quadratic"];
      Labeled[c,"quadratic drag coefficient c"]
      Labeled[q,"quadratic drag: {maximum range, optimal angle, landing time}"]
      Labeled[UnitConvert[Part[q,1]-R,"m"],"maximum-range calibration residual"]
      Labeled[Plot[ProjectileRange[c,m,v,g,θ,"Quadratic"],{θ,0°,90°}],"quadratic drag range versus launch angle [rad]"]'''),
      text('### 运动轨迹\n\n取拟合后的阻力系数和最佳投射角，求速度、位移及落地前的轨迹。'),
      calc('''θ=Part[q,2];
      u=ProjectileVelocity[c,m,v,g,θ,{t,0[s],Part[q,3]},"Quadratic"];
      r=Integrate[u,{t,0[s],t*1[s]}];
      Labeled[u,"quadratic drag velocity, {vx,vy}"]
      Labeled[r,"quadratic drag displacement, {x,y}"]
      Labeled[Plot[Part[r,1],{t,0[s],Part[q,3]}],"quadratic drag horizontal displacement versus time"]
      Labeled[Plot[Part[r,2],{t,0[s],Part[q,3]}],"quadratic drag vertical displacement versus time"]'''),
      calc('Labeled[Animate[ParametricPlot[r,{t,0[s],Part[q,3]}]],"quadratic drag flight to landing"]'),
    ]}
