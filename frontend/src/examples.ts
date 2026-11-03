const groupOrder = ['显式数值计算', '解析与符号计算', '统计分析', '数值求解', '后处理'];
export const numericalPools = [
  ['1 + 1', '2^10 - 3^4', '(17 + 23) (19 - 7)', 'Sqrt[144] + 5!'],
  ['N[Sqrt[2], 50]', 'N[Pi, 60]', 'N[E, 40]', 'N[Log[2], 50]'],
  ['N[Sin[30°] + Cos[Pi/3], 20]', 'Sin[90°]', 'Cos[Pi/6]^2', 'N[ArcTan[1], 25]'],
  ['Simplify[(3+4*I)/(1-2*I)]', 'Expand[(2-3*I)^4]', 'Simplify[Conjugate[(1+2*I)/(3-I)]]', 'Expand[Sqrt[-7]+(2-I)^3]'],
  ['Binomial[50, 6]', '20!', 'Binomial[30, 10]', '15! / (5! 10!)'],
  ['Sum[k^2, {k, 1, 100}]', 'Sum[1/n^2, {n, 1, Infinity}]', 'Sum[1/2^k, {k, 0, 20}]', 'Sum[k^3, {k, 1, 50}]'],
  ['Product[1+1/k, {k, 1, 20}]', 'Product[k, {k, 1, 12}]', 'Product[(k+2)/k, {k, 1, 10}]', 'Product[1-1/k^2, {k, 2, 20}]'],
  ['N[Hypergeometric2F1[1/2,1/2,1,1/2],40]', 'N[Hypergeometric1F1[1,2,1],30]', 'N[Hypergeometric0F1[2,1],30]', 'N[Gamma[1/3]+BesselJ[0,1],30]'],
  ['Dot[{{1,2},{3,4}},{{2,0},{1,2}}]', 'Inverse[{{1,2},{3,4}}]', 'Transpose[{{1,2,3},{4,5,6}}]', 'Dot[{{2,-1,0},{1,3,2}},{{1,2},{0,1},{-1,3}}]'],
  ['Det[{{1,2,3},{0,4,5},{1,0,6}}]', 'Det[{{2,-1,0},{-1,2,-1},{0,-1,2}}]', 'Det[{{1,2,3,4},{0,2,1,3},{0,0,3,2},{0,0,0,4}}]', 'Det[{{3,1,-1},{2,4,1},{-1,2,5}}]'],
];
const bundle = (codes: string[]) => codes.join('\n');
const compactNames: Record<string,string> = { data: 'd', dist: 'p', residuals: 'r', ys: 'y₁', sse: 's', r2: 'r₂', row: 'q', logData: 'd₂', logFit: 'f₂', rec: 'r' };
const compactExample = (code: string) => code.replace(/"(?:[^"\\]|\\.)*"|[A-Za-z][A-Za-z0-9]*/g, token => compactNames[token] || token);
export function numericalExample(previous = '') {
  return bundle(numericalPools.map(pool => {
    const choices = pool.filter(code => !previous.includes(code));
    return choices[Math.floor(Math.random() * choices.length)];
  }));
}

export const examples = [
  { group: '解析与符号计算', title: '偏微分方程解析解', component:'pde', codes: [
    'Clear[u,x,y];\nv=DSolveValue[{D[u[x,y],{y,2}]==-6,u[x,0]==0,u[x,1]==0},u[x,y],{x,y}];\nv\nPlot[v,{y,0,1}]',
    'Clear[u,x,t];\nv=DSolveValue[{D[u[x,t],t]==D[u[x,t],{x,2}],u[0,t]==0,u[1,t]==0,u[x,0]==Sin[Pi*x]},u[x,t],{x,t}];\nv\nPlot3D[v,{x,0,1},{t,0,1}]',
    'Clear[u,x,t];\nv=DSolveValue[{D[u[x,t],{t,2}]==4*D[u[x,t],{x,2}],u[0,t]==0,u[1,t]==0,u[x,0]==Sin[Pi*x]},u[x,t],{x,t}];\nv\nPlot3D[v,{x,0,1},{t,0,1}]',
    'Clear[u,x,y];\nDSolve[{D[u[x,y],x]+D[u[x,y],y]==0},u[x,y],{x,y}]',
  ] },
  { group:'数值求解',title:'偏微分方程数值解',component:'pde',codes:[
    'Clear[u,x,y];\nv=NDSolveValue[{Laplacian[u[x,y],{x,y}]==-2*Pi^2*Sin[Pi*x]*Sin[Pi*y],u[0,y]==0,u[1,y]==0,u[x,0]==0,u[x,1]==0},u[x,y],{x,0,1},{y,0,1}];\nPDEValue[v,{1/2,1/2}]\nPDEPlot[v,"Solution"]',
    'Clear[u,x,t];\nv=NDSolveValue[{D[u[x,t],t]==D[u[x,t],{x,2}],u[0,t]==0,u[1,t]==0,u[x,0]==Sin[Pi*x]},u[x,t],{x,0,1},{t,0,1}];\nPDEValue[v,{1/2,1/10}]\nPDEPlot[v,"Solution"]',
    'Clear[u,x,y];\nNDEigensystem[-Laplacian[u[x,y],{x,y}],u[x,y],{x,0,1},{y,0,1},5]',
  ] },
  { group: '显式数值计算', title: '显式数值计算', codes: [0,1,2,3].map(i => bundle(numericalPools.map(pool => pool[i]))) },
  { group: '显式数值计算', title: '单位换算与运算', codes: [
    bundle(['UnitConvert[3[m]+20[cm],"cm"]', 'UnitConvert[0[degC],"K"]', 'UnitConvert[72[km/h],"m/s"]', 'UnitConvert[1[bar],"Pa"]', 'UnitConvert[1[kWh],"J"]', '[kg*m/s^2]', '[N/m^2]', '2["牛顿"]*3["米"]', '1[kg/(m*s)]', '10[m/s]*2[s]']),
    bundle(['UnitConvert[1[inch],"cm"]', 'UnitConvert[100[degC],"degF"]', 'UnitConvert[9.81[m/s^2],"cm/s^2"]', 'UnitConvert[1[L],"cm^3"]', 'UnitConvert[1[atm],"kPa"]', '2[kg]*3[m/s^2]', '12[J]/3[m]', '10[N]*2[m]', '100[W]*3[s]', '12[V]/2[A]']),
    bundle(['UnitConvert[1["µm"],"nm"]', 'UnitConvert[1[m^2],"cm^2"]', 'UnitConvert[1[eV],"J"]', 'UnitConvert[60[mile/h],"km/h"]', 'UnitConvert[32[degF],"degC"]', '[V]*[A]', '[A]*[s]', '[kg*m^2/s^3]', '[T]*[m^2]', '1[kg*m^2/(s^3*K)]']),
  ] },
  { group: '统计分析', title: '描述统计', codes: [
    'data={72,81,85,85,90,94,98};\nMean[data]\nMedian[data]\nVariance[data]\nStandardDeviation[data]\nQuartiles[data]\nCounts[data]\nHistogram[data,5]',
    'data={12,15,18,18,19,21,24,28};\nMean[data]\nQuantile[data,{1/4,1/2,3/4}]\nInterquartileRange[data]\nSkewness[data]\nKurtosis[data]\nStandardize[data]\nHistogram[data,4]',
  ] },
  { group: '统计分析', title: '概率分布', codes: [
    'dist=NormalDistribution[100,15];\nMean[dist]\nVariance[dist]\nN[CDF[dist,115],10]\nN[InverseCDF[dist,975/1000],10]\nPlot[PDF[dist,x],{x,40,160}]',
    'dist=BinomialDistribution[10,1/2];\nMean[dist]\nVariance[dist]\nPDF[dist,5]\nCDF[dist,5]\nListPlot[{{0,PDF[dist,0]},{1,PDF[dist,1]},{2,PDF[dist,2]},{3,PDF[dist,3]},{4,PDF[dist,4]},{5,PDF[dist,5]},{6,PDF[dist,6]},{7,PDF[dist,7]},{8,PDF[dist,8]},{9,PDF[dist,9]},{10,PDF[dist,10]}}]',
    'dist=ExponentialDistribution[1/5];\nMean[dist]\nStandardDeviation[dist]\nCDF[dist,5]\nPlot[PDF[dist,x],{x,0,25}]',
    'dist=PoissonDistribution[3];\nMean[dist]\nVariance[dist]\nPDF[dist,2]\nN[CDF[dist,5],12]',
  ] },
  { group: '统计分析', title: '相关与回归', codes: [
    'data={{1,2},{2,3},{3,5},{4,4},{5,6}};\nf=Fit[data,{1,x},x];\nf\nCorrelation[{1,2,3,4,5},{2,3,5,4,6}]\nListPlot[data]\nPlot[f,{x,0,6}]',
    'Covariance[{1,2,3,4},{2,4,5,8}]\nCorrelation[{1,2,3,4},{2,4,5,8}]\nSpearmanRho[{1,2,2,4},{4,1,2,3}]\nFit[{{0,1},{1,2},{2,5},{3,10}},{1,x,x^2},x]',
  ] },
  { group: '统计分析', title: '假设检验', codes: [
    'data={98,101,99,103,100,102,97,104};\nMean[data]\nStandardDeviation[data]\nTTest[data,100]\nZTest[data,100,3]\nHistogram[data,4]',
    'data={11,12,9,14,13,10,15,12};\nMean[data]\nTTest[data,10]\nZTest[data,10,2]\nListPlot[data]',
  ] },
  { group: '统计分析', title: '数据拟合', codes: [
    'data={{0,0.1},{1,2.2},{2,4.0},{3,6.1},{4,7.9},{5,10.2}};\nf=Fit[data,{1,x},x];\nresiduals=Table[Part[row,2]-ReplaceAll[f,x->Part[row,1]],{row,data}];\nsse=Total[Table[e^2,{e,residuals}]];\nys=Table[Part[row,2],{row,data}];\nr2=1-sse/Total[Table[(y-Mean[ys])^2,{y,ys}]];\nf\nN[r2,8]\nN[Sqrt[sse/Length[data]],8]\nShow[ListPlot[data],Plot[f,{x,0,5},PlotLegends->{"linear fit"}]]\nListPlot[Table[{Part[data,i,1],Part[residuals,i]},{i,1,Length[data]}]]',
    'data={{0,1.1},{1,3.9},{2,8.8},{3,16.2},{4,25.1},{5,35.9}};\nf=Fit[data,{1,x,x^2},x];\nresiduals=Table[Part[row,2]-ReplaceAll[f,x->Part[row,1]],{row,data}];\nf\nN[Sqrt[Mean[Table[e^2,{e,residuals}]]],8]\nShow[ListPlot[data],Plot[f,{x,0,5},PlotLegends->{"quadratic fit"}]]\nListPlot[Table[{Part[data,i,1],Part[residuals,i]},{i,1,Length[data]}]]',
    'data={{0,10.1},{1,7.2},{2,5.3},{3,3.8},{4,2.7},{5,2.0}};\nlogData=Table[{Part[row,1],Log[Part[row,2]]},{row,data}];\nlogFit=Fit[logData,{1,x},x];\nf=Exp[logFit];\nresiduals=Table[Part[row,2]-ReplaceAll[f,x->Part[row,1]],{row,data}];\nN[f,8]\nN[Sqrt[Mean[Table[e^2,{e,residuals}]]],8]\nShow[ListPlot[data],Plot[f,{x,0,5},PlotLegends->{"exponential fit"}]]\nListPlot[Table[{Part[data,i,1],Part[residuals,i]},{i,1,Length[data]}]]',
  ] },
  { group: '解析与符号计算', title: '因式分解', codes: [
    'Factor[x^10-x^8-5*x^6+x^4+8*x^2+4]',
    'Factor[x^6-4*x^5*y+7*x^4*y^2-8*x^3*y^3+7*x^2*y^4-4*x*y^5+y^6]',
    'Factor[x^8+4*x^6+6*x^4+4*x^2+1]',
  ] },
  { group: '解析与符号计算', title: '有理式化简', codes: [
    'Cancel[(x^8-1)/(x^6+x^4+x^2+1)]',
    'Together[1/(x-1)-1/(x+1)-2/(x^2-1)]',
    'Cancel[(x^6-y^6)/((x-y)*(x^2+x*y+y^2)*(x^2-x*y+y^2))]',
  ] },
  { group: '解析与符号计算', title: '级数展开', codes: [
    'Series[Log[(1+x)/(1-x)]-2*x-2*x^3/3-2*x^5/5,{x,0,10}]',
    'Series[(Exp[x]-1-x-x^2/2-x^3/6)/x^4,{x,0,4}]',
    'Series[(Sin[x]-x*Cos[x])/x^3,{x,0,6}]',
  ] },
  { group: '解析与符号计算', title: '三角函数展开', codes: [
    'Simplify[TrigExpand[Sin[3*x]*Cos[2*x]-Cos[3*x]*Sin[2*x]]]',
    'Simplify[TrigExpand[Cos[x+y]*Cos[x-y]+Sin[x+y]*Sin[x-y]]]',
    'TrigExpand[Sin[2*x+2*y]]',
  ] },
  { group: '解析与符号计算', title: '复数化简', codes: [
    'Simplify[ComplexExpand[(x+I*y)/(x-I*y)+(x-I*y)/(x+I*y)]]',
    'Factor[ComplexExpand[Conjugate[(x+I*y)^3]*(x+I*y)^3]]',
    'Simplify[ComplexExpand[Exp[I*x]*(Cos[x]-I*Sin[x])]]',
  ] },
  { group: '解析与符号计算', title: '参数积分', codes: ['Integrate[Exp[-a x], {x, 0, Infinity}]', 'Integrate[Exp[-x^2], x]', 'Integrate[x Sin[x], x]'] },
  { group: '解析与符号计算', title: '解析最值', codes: [
    'Minimize[x^2-4 x+5,x]\nMaximize[4-x^2,{x,-3,3}]\nPlot[{x^2-4 x+5,4-x^2},{x,-3,4}]',
    'Minimize[x^4-2 x^2,{x,-2,2}]\nMaximize[x (4-x),{x,0,4}]\nPlot[x^4-2 x^2,{x,-2,2}]',
  ] },
  { group: '解析与符号计算', title: '符号求导', codes: ['D[Sin[x^2], x]', 'D[x^3 y^2, {x, 2}, y]', 'D[Log[1+x^2], x]'] },
  { group: '解析与符号计算', title: '代数方程组', codes: [
    'Solve[{x+y==3,x-y==1},{x,y}]\nPlot[{3-x,x-1},{x,0,4}]',
    'Solve[{x^2+y^2==5,x-y==1},{x,y}]\nContourPlot[(x^2+y^2-5) (x-y-1),{x,-3,3},{y,-3,3}]',
    'Solve[x^4-5 x^2+4==0,x]\nPlot[x^4-5 x^2+4,{x,-2.5,2.5}]',
  ] },
  { group: '解析与符号计算', title: '差分方程', codes: [
    'rec = RSolve[{q[n+1]==2 q[n]+1,q[0]==0},q[n],n];\nrec\nPlot[ReplaceAll[q[n],rec],{n,0,10}]',
    'rec = RSolve[{q[n+1]==q[n]+n,q[0]==0},q[n],n];\nrec\nPlot[ReplaceAll[q[n],rec],{n,0,20}]',
  ] },
  { group: '解析与符号计算', title: '微分方程解析解', codes: [
    "f = DSolveValue[{y'[x]==-2 y[x],y[0]==1},y[x],x];\nf\nPlot[f,{x,0,5}]",
    "f = DSolveValue[{y''[x]+y[x]==0,y[0]==1,y'[0]==0},y[x],x];\nf\nPlot[f,{x,0,4 Pi}]",
    "v = DSolveValue[{vx'[t]==-vx[t]/5,vy'[t]==-981/100-vy[t]/5,vx[0]==10,vy[0]==15},{vx[t],vy[t]},t];\nv\nPlot[v,{t,0,3}]",
  ] },
  { group: '数值求解', title: '数值求根', codes: ['FindRoot[Cos[x]-x,{x,0,1}]\nPlot[Cos[x]-x,{x,0,1}]'] },
  { group: '数值求解', title: '数值最值', codes: [
    'FindMinimum[(x-1.3)^2+Exp[x]/10,{x,-2,3}]\nPlot[(x-1.3)^2+Exp[x]/10,{x,-2,3}]',
    'FindMaximum[Sin[x],{x,0,Pi}]\nPlot[Sin[x],{x,0,Pi}]',
  ] },
  { group: '数值求解', title: '数值积分', codes: ['NIntegrate[Exp[-x^2],{x,-3,3}]\nPlot[Exp[-x^2],{x,-3,3}]'] },
  { group: '数值求解', title: 'ODE 初值问题', codes: ["NDSolve[{y'[t]==-y[t]+Sin[t],y[0]==1},y,{t,0,15}]"] },
  { group: '后处理', title: '三维曲面', codes: ['Plot3D[Sin[x] Cos[y],{x,-Pi,Pi},{y,-Pi,Pi}]'] },
  { group: '后处理', title: '等高线', codes: ['ContourPlot[x^2-y^2,{x,-3,3},{y,-3,3}]'] },
  { group: '后处理', title: '二维参数曲线', codes: ['ParametricPlot[{Cos[3 t],Sin[2 t]},{t,0,2 Pi}]'] },
  { group: '后处理', title: '三维参数曲线', codes: ['ParametricPlot3D[{Cos[t],Sin[t],t/4},{t,0,6 Pi}]'] },
  { group: '后处理', title: '参数曲面', codes: ['ParametricPlot3D[{(2+Cos[v]) Cos[u],(2+Cos[v]) Sin[u],Sin[v]},{u,0,2 Pi},{v,0,2 Pi}]'] },
  { group: '后处理', title: '动画', codes: [
    'Animate[ParametricPlot[{Cos[t],Sin[t]},{t,0,2 Pi}]]',
    'Animate[Plot[Sin[x-a],{x,-Pi,Pi}],{a,0,2 Pi}]',
    'Animate[ParametricPlot[{Cos[3 t],Sin[2 t]},{t,0,2 Pi}]]',
  ] },
].map(example => ({ ...example, codes: example.codes.map(compactExample) })).sort((a,b) => groupOrder.indexOf(a.group)-groupOrder.indexOf(b.group)
  || Number(a.title === '偏微分方程解析解')-Number(b.title === '偏微分方程解析解'));
