# Calix 0.1.17

机翼与吊桥示例改为在计算单元中明确构造网格、材料系数、方程和约束。
示例不再调用 `WingFlowSolve`、`FEMBridgeSolve` 或 `PDEPlot`。

- 吊桥：1024 个四边形桥面单元、2048 个六面体塔体单元，主缆及吊杆为
  一维预张紧桁架。通过 `InitializePDECoefficients`、`DiscretizePDE` 和
  `LinearSolve` 组装混合维系统，输出位移、应变能、平衡误差与最小索张力。
- 机翼：3456 个贴体四边形，速度 Q2、压力 Q1。采用
  `FluidFlowPDEComponent`、`DirichletCondition` 和 `NDSolveValue`，混合长度
  涡黏度表达式写在笔记本中，后处理使用 `DensityPlot` 和 `StreamPlot`。
- C++ 核心：结构单元的高斯积分、系数张量收缩和局部刚度计算使用
  Eigen；桥梁与机翼的稀疏线性系统使用 Eigen SparseLU，包含尺度平衡和
  迭代修正。机翼的非线性迭代及 Q2/Q1 装配由 Python/scikit-fem 调度。
- 类氢离子：由径向薛定谔方程计算级数递推、终止条件、能级及归一化径向
  函数；角向多项式也由分离后的方程求出。六个定态均检验原方程和归一化。
- 新安装默认 Workers 上限取 Windows 报告的物理核心数，保留已有用户设置。
  本次验证统一设置 `CALIX_MAX_WORKERS=8`；每个计算进程的 BLAS 限制为一线程。
- 缩短案例中的罗列式标题，保留物理假设、边界条件和必要的结果说明。

Eigen 3.4.0 使用 MPL-2.0 许可，并启用 `EIGEN_MPL2_ONLY`。安装包附完整原版
源码归档和许可文本。Calix 自有代码仍为闭源。

这是已明确限定范围的 Wolfram 语法子集。吊桥为预张紧平衡构型上的线性
增量分析；机翼的代数湍流闭合不用于预测转捩、失速或分离。网格加密结果
用于评估离散误差，代数残差不能替代物理验证。
