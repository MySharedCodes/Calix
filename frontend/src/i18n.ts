import { useSyncExternalStore } from 'react';
import { savePreference } from './preferences';
import type { ExtraLanguage } from './locales';
let extraTranslations: Partial<Record<ExtraLanguage, Record<string, string>>> = {};
let extraInstalled = false;

export type Language = 'zh' | 'en' | ExtraLanguage;
export const languages: { code: Language; name: string }[] = [
  { code: 'zh', name: '简体中文' }, { code: 'en', name: 'English' },
  { code: 'ja', name: '日本語' }, { code: 'fr', name: 'Français' },
  { code: 'ru', name: 'Русский' }, { code: 'de', name: 'Deutsch' }, { code: 'es', name: 'Español' },
];
const savedLanguage = localStorage.getItem('calix-language');
let language: Language = languages.find(item => item.code === savedLanguage)?.code || 'zh';
document.documentElement.lang = language === 'zh' ? 'zh-CN' : language;
const listeners = new Set<() => void>();
export const translations: Record<string, string> = {
  '含未求值函数': 'Contains unevaluated functions',
  '恢复历史': 'Recovery history', '恢复版本': 'Recovery versions', '浏览器备份': 'Browser backup', '最近副本': 'Latest copy',
  '选择恢复版本': 'Select a recovery version', '暂无恢复历史': 'No recovery history', '恢复数据无效': 'Invalid recovery data', ' 恢复副本': ' recovered copy',
  '撤销单元操作': 'Undo cell operation', '重做单元操作': 'Redo cell operation', '笔记最多包含 200 个单元': 'A notebook can contain up to 200 cells',
  '磁盘恢复副本写入失败，请将笔记保存到文件': 'Disk recovery copy failed. Save your notebooks to files.',
  '帮助': 'Help', '关闭帮助': 'Close help', '帮助目录': 'Help topics', '搜索帮助': 'Search help',
  '帮助正文': 'Help article', '没有匹配的文档': 'No matching articles', '文件位置': 'File location',
  '快速上手': 'Get started (中文)', '使用帮助': 'User guide (中文)', '故障排查': 'Troubleshooting (中文)',
  '案例目录': 'Example catalog (中文)', '安装说明': 'Installation (中文)', '开发与构建': 'Development (中文)', '文档目录': 'Documentation index (中文)',
  '换算单位':'Convert','复数式':'Complex',
  '行列式':'Determinant','逆矩阵':'Inverse','平均值':'Mean','标准差':'Std. deviation','转置':'Transpose','特征值':'Eigenvalues','通分':'Fractions',
  '解析最小值':'Exact minimum','解析最大值':'Exact maximum','数值最小值':'Numerical minimum','数值最大值':'Numerical maximum',
  '此功能需要 PDE module。请重新运行安装包并勾选 PDE module。':'This feature requires PDE module. Run the installer again and select PDE module.',
  '波动光学：石英与空气的反射和折射':'Wave optics: reflection and refraction at quartz and air',
  '格点色动力学：SU(3) 规范场与 Wilson 环':'Lattice QCD: SU(3) gauge fields and Wilson loops',
  '复制到下一行输入':'Copy to a new input below', '结果过长或单元数量已达上限':'Result is too long or the cell limit has been reached',
  '页面皮肤':'Appearance', '简洁白':'Clean white','深空黑':'Deep space black','少女粉':'Soft pink','海洋蓝':'Ocean blue','森林绿':'Forest green',
  '已安装':'Installed','未安装':'Not installed',
  '偏微分方程解析解':'Analytical PDE solutions','偏微分方程数值解':'Numerical PDE solutions',
  '吊桥：混合维有限元受力分析':'Suspension bridge: mixed-dimensional finite elements',
  '机翼：稳态流场与湍流闭合':'Wing: steady flow and turbulence closure',
  '特殊符号': 'Special symbols', '特殊符号缩写': 'Symbol abbreviation', '未找到特殊符号': 'Special symbol not found',
  '下标需要单字母和非负整数': 'Subscripts require a single letter and a nonnegative integer',
  'Notebook': 'Notebook', 'Calculator': 'Calculator',
  '电流线圈附近的带电粒子': 'Charged particles near coaxial current loops',
  '类氢离子：薛定谔方程解析解': 'Hydrogen-like ion: analytical Schrodinger solution',
  '弹性双摆：两段弹簧与两个小球': 'Elastic double pendulum: two springs and two masses',
  '五球弹簧串：松手下落': 'Five-mass spring chain: free release',
  '打开文件位置': 'Open file location', '同时删除磁盘源文件': 'Also delete the source file on disk',
  '确认删除源文件': 'Confirm source file deletion', '永久删除源文件': 'Permanently delete source file',
  '将永久删除以下源文件，不会放入回收站。此操作无法撤销。': 'The following source file will be permanently deleted without using the Recycle Bin. This cannot be undone.',
  '此笔记尚未保存到磁盘': 'This notebook has not been saved to disk',
  '文件位置与源文件删除功能仅在桌面版可用': 'File location and source file deletion are available in the desktop app',
  '下一步': 'Next', '处理中': 'Processing',
  '假设检验': 'Hypothesis tests',
  '高考物理：2016 全国Ⅲ卷第25题最后一问': 'Gaokao Physics: 2016 Paper III, Problem 25, final part',
  '高考数学：2008 江西理科第22题': 'Gaokao Mathematics: 2008 Jiangxi, Problem 22',
  '高考数学：2022 全国乙卷理科第20题': 'Gaokao Mathematics: 2022 Paper B, Problem 20',
  'IMO 1979 第1题：交错调和和': 'IMO 1979 Problem 1: alternating harmonic sum',
  'IMO 1978 第1题：幂的末三位': 'IMO 1978 Problem 1: last three digits of powers',
  '三天体：平面引力运动': 'Three bodies: planar gravitational motion',
  '空气阻力下的二维抛体运动': 'Projectile motion with air resistance',
  '多天体：平面与三维引力运动': 'Many bodies: planar and spatial gravitation',
  '数据拟合': 'Data fitting', '同轴线圈': 'Coaxial coils', '磁感线': 'Magnetic field lines',
  '单位运算器': 'Unit calculator', '单位运算': 'Unit arithmetic', '单位换算与运算': 'Unit conversion and arithmetic', '单位表达式': 'Unit expression', '计算': 'Calculate', '插入计算单元': 'Insert calculation cell',
  '统计分析': 'Statistics', '描述统计': 'Descriptive statistics', '概率分布': 'Probability distributions', '相关与回归': 'Correlation and regression',
  '解析与符号计算': 'Analytical and symbolic calculations', '因式分解': 'Factorization', '有理式化简': 'Rational simplification', '级数展开': 'Series expansions', '三角函数展开': 'Trigonometric expansions', '复数化简': 'Complex simplification',
  'IMO 1981 第3题：整数约束下的最大值': 'IMO 1981 Problem 3: An integer-constrained maximum',
  'IPhO 2011 第3题：离子散射与俘获截面': 'IPhO 2011 Problem 3: Ion scattering and capture cross section',
  '个单元': 'cells', '文件历史': 'File history',
  '文件': 'File', '工作空间': 'Workspace', '新建笔记': 'New notebook', '打开': 'Open', '保存': 'Save', '另存为': 'Save as',
  '传统计算器面板': 'Calculator panel', '计算示例': 'Examples', '偏好设置': 'Preferences', '关闭设置': 'Close preferences',
  '笔记管理': 'Notebooks', '重命名笔记': 'Rename notebook', '复制笔记': 'Duplicate notebook', '移除笔记': 'Remove notebook',
  '笔记名称': 'Notebook name', 'Notebook 名称': 'Notebook name', '取消': 'Cancel', '关闭': 'Close', '移除': 'Remove',
  '仅移除工作空间中的副本，磁盘文件不受影响。': 'Remove the workspace copy. Files on disk are kept.', '未命名笔记': 'Untitled CIX notebook', ' 副本': ' copy',
  '全部运行': 'Run all', '停止计算': 'Stop calculation', '重启会话': 'Restart session', '清空全部输出': 'Clear all outputs', '计算单元': 'Calculation cell', '文字单元': 'Text cell',
  '恢复 100%': 'Reset to 100%', '运行单元': 'Run cell', '上移单元': 'Move cell up', '下移单元': 'Move cell down',
  '复制单元': 'Duplicate cell', '删除单元': 'Delete cell', '添加计算单元': 'Add calculation cell', '待重新计算': 'Needs recalculation',
  '计算中': 'Calculating', '就绪': 'Ready', '本地计算': 'Local computation', '收起侧栏': 'Collapse sidebar', '展开侧栏': 'Expand sidebar',
  '连接引擎': 'Connecting', '引擎离线': 'Engine offline', '原生核心就绪': 'Native engine ready', '符号引擎就绪': 'Symbolic engine ready',
  '重新连接': 'Reconnect', '关闭示例': 'Close examples', '关闭通知': 'Dismiss notification', '复制结果': 'Copy result', '保留符号形式': 'Symbolic form retained',
  '显式数值计算': 'Explicit numerical calculations', '单位换算': 'Unit conversion', '解析求解': 'Analytical solving', '数值求解': 'Numerical solving', '后处理': 'Postprocessing',
  '参数积分': 'Parametric integration', '符号求导': 'Symbolic differentiation', '代数方程组': 'Algebraic equations', '差分方程': 'Difference equations',
  '微分方程解析解': 'Analytical ODE solutions', '解析最值': 'Analytical extrema', '数值最值': 'Numerical extrema',
  '数值求根': 'Numerical roots', '数值积分': 'Numerical integration', 'ODE 初值问题': 'ODE initial value problem',
  '三维曲面': '3D surface', '等高线': 'Contours', '二维参数曲线': '2D parametric curve', '三维参数曲线': '3D parametric curve', '参数曲面': 'Parametric surface', '动画': 'Animation',
  '线性空气阻力下的二维抛体运动': 'Projectile motion with linear drag',
  '数值近似有效位数': 'Numerical precision', '最大 CPU Workers': 'Maximum CPU Workers', '界面语言': 'Language', '计算核心': 'Computation engine', '版本': 'Version', '许可证': 'License',
  'Notebook 已保存': 'Notebook saved', '已打开 Notebook；会话变量已清空': 'Notebook opened with a new calculation session',
  '计算已停止，会话变量已清空': 'Calculation stopped; session variables cleared', '计算会话已重启': 'Calculation session restarted',
  '自动保存失败，请将 Notebook 保存到文件': 'Autosave failed. Save the notebook to a file.', '请先停止当前计算': 'Stop the current calculation first',
  '计算引擎正在启动，请稍后打开文件': 'The engine is starting. Open the file when it is ready.', 'Notebook 文件超过 10 MB': 'Notebook file exceeds 10 MB',
  '不是有效的 Calix Notebook v1 文件': 'Invalid Calix Notebook v1 file', 'Notebook 标题无效': 'Invalid notebook title', 'Notebook 单元无效': 'Invalid notebook cell', '数学输入内容无效': 'Invalid formula input',
  '计算引擎尚未连接': 'The computation engine is not connected', '工作空间存储已满，请将笔记保存到文件': 'Workspace storage is full. Save notebooks to files.',
  '最多保留 100 个笔记，请先导出并移除部分笔记': 'Workspace holds up to 100 notebooks. Export and remove some notebooks first.',
  '预览文字单元': 'Preview text cell', '编辑文字单元': 'Edit text cell', '文字单元内容': 'Text cell content',
  '文字格式': 'Text formatting', '段落样式': 'Paragraph style', '正文': 'Normal text', '标题': 'Heading', '字号': 'Font size', '默认字号': 'Default size',
  '粗体': 'Bold', '斜体': 'Italic', '下划线': 'Underline', '删除线': 'Strikethrough', '项目符号': 'Bullet list', '编号列表': 'Numbered list',
  '清除格式': 'Clear formatting', '撤销': 'Undo', '重做': 'Redo', 'Markdown 源码': 'Markdown source', '文字单元最多 24000 个字符': 'Text cells support up to 24,000 characters',
  '笔记本目录': 'Notebook contents', '目录': 'Contents', '打开目录': 'Open contents', '关闭目录': 'Close contents', '搜索标题': 'Search headings',
  '标题列表': 'Headings', '未命名标题': 'Untitled heading', '没有匹配的标题': 'No matching headings',
  '数学表达式': 'Math expression', '插入公式': 'Insert formula', '插入': 'Insert', '公式输入': 'Formula input', '关闭公式输入': 'Close formula input',
  '输入表达式…': 'Enter an expression…', '数学表达式尚未完成': 'The formula is incomplete', '不支持的数学输入结构': 'Unsupported formula structure', '数学表达式尚未完成或无法解析': 'The formula is incomplete or cannot be parsed',
  '播放动画': 'Play animation', '暂停动画': 'Pause animation', '重置动画': 'Reset animation', '动画进度': 'Animation progress', '动画参数': 'Animation parameter', '动画速度': 'Animation speed', '循环': 'Loop',
  '重置视图': 'Reset view', '导出 PNG': 'Export PNG', '三维绘图': '3D plot', '三维绘图没有有效的实数采样点': 'No valid real samples for the 3D plot',
  '不透明度': 'Opacity', '透明度映射': 'Opacity mapping',
  '计算器输入': 'Calculator input', '删除': 'Delete', '数值近似': 'Approximate', '结果已复制': 'Result copied', '上一页按钮': 'Previous keypad page', '下一页按钮': 'Next keypad page',
  '按钮页': 'Keypad pages', '基础': 'Basic', '函数': 'Functions', '求解': 'Solvers', '历史记录': 'History', '清空历史': 'Clear history', '多个结果': 'Multiple results',
  '共轭': 'Conjugate', '参数曲线': 'Parametric curve',
  '石英与空气：电磁波反射和透射': 'Quartz and air: electromagnetic reflection and transmission',
  '齿轮啮合：接触与扭矩传递': 'Meshing gears: contact and torque transmission',
};
export function t(text: string): string {
  if (language === 'zh') return text;
  return (language === 'en' ? translations[text] : extraTranslations[language]?.[text]) || translations[text] || text;
}
export function installTranslations(data: typeof extraTranslations) { extraTranslations = data; extraInstalled = true; listeners.forEach(listener => listener()); }
export function availableLanguages() { return languages.filter(item => extraInstalled || ['zh','en'].includes(item.code)); }
export function restrictLanguage() { if (!extraInstalled && !['zh','en'].includes(language)) setLanguage('en'); }
export function setLanguage(value: Language) {
  if (!languages.some(item => item.code === value)) return;
  language = value; savePreference('calix-language', value); document.documentElement.lang = value === 'zh' ? 'zh-CN' : value;
  listeners.forEach(listener => listener());
}
export function useLanguage() {
  return useSyncExternalStore(listener => { listeners.add(listener); return () => { listeners.delete(listener); }; }, () => language);
}
