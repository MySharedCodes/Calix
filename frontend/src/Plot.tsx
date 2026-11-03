import { plotPalette } from './themes';
import { activatePlotWheel } from './plotInteraction';
import { t } from './i18n';
import { useEffect, useRef, useState } from 'react';
import { Download, RotateCcw } from 'lucide-react';
import type { PlotResult } from './types';

const colors = ['#087e80', '#d45b61', '#b18b23', '#6655af'];

export function Plot({ result, frame, cursor, trajectory = false }: { result: PlotResult; frame?: PlotResult; cursor?: number; trajectory?: boolean }) {
  const host = useRef<HTMLDivElement>(null);
  const [error, setError] = useState('');
  const resetRef = useRef<() => void>(() => {});
  const exportRef = useRef<() => void>(() => {});
  const updateRef = useRef<(frame?: PlotResult, cursor?: number) => void>(() => {});
  const [ready, setReady] = useState(0);
  const is3d = ['surface', 'curve3d', 'parametric_surface'].includes(result.plot_type);

  useEffect(() => {
    let dispose = () => {};
    let cancelled = false;
    setError('');
    (async () => {
      if (is3d) {
        const THREE = await import('three');
        const { OrbitControls } = await import('three/addons/controls/OrbitControls.js');
        if (cancelled || !host.current) return;
        const element = host.current;
        const releaseWheel = activatePlotWheel(element);
        const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
        renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
        renderer.setClearColor(plotPalette().background);
      const recolor = () => renderer.setClearColor(plotPalette().background); window.addEventListener('calix-theme-change', recolor);
        renderer.domElement.setAttribute('aria-label', t("三维绘图"));
        element.appendChild(renderer.domElement);
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(40, 1, 0.01, 1000);
        const controls = new OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        const object = new THREE.Group();
        const vertexPositions: number[] = [];
        const indices: number[] = [];
        const vertexColors: number[] = [];
        const valid: boolean[] = [];
        let surfaceGeometry: import('three').BufferGeometry | undefined;
        let colorLow = 0, colorHigh = 1;
        if (result.plot_type === 'curve3d') {
          const trace = result.traces![0];
          let segment: import('three').Vector3[] = [];
          const flush = () => {
            if (segment.length > 1) object.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(segment), new THREE.LineBasicMaterial({ color: colors[0] })));
            segment = [];
          };
          trace.x.forEach((x, i) => {
            const y = trace.y[i], z = trace.z![i];
            if (x === null || y === null || z === null) flush();
            else segment.push(new THREE.Vector3(x, z, -y));
          });
          flush();
        } else {
          const count = result.size || result.x!.length;
          for (let j = 0; j < count; j++) for (let i = 0; i < count; i++) {
            const index = j * count + i;
            const x = result.coordinates ? result.coordinates[0][index] : result.x![i];
            const y = result.coordinates ? result.coordinates[1][index] : result.y![j];
            const z = result.coordinates ? result.coordinates[2][index] : result.z![j][i];
            valid.push(x !== null && y !== null && z !== null);
            vertexPositions.push(x ?? 0, z ?? 0, -(y ?? 0));
          }
          for (let j = 0; j < count - 1; j++) for (let i = 0; i < count - 1; i++) {
            const a = j * count + i, b = a + 1, c = a + count, d = c + 1;
            if ([a, b, c].every(k => valid[k])) indices.push(a, c, b);
            if ([b, c, d].every(k => valid[k])) indices.push(b, c, d);
          }
          const heights = vertexPositions.filter((_, i) => i % 3 === 1);
          const low = result.options?.range?.[0] ?? Math.min(...heights), high = result.options?.range?.[1] ?? Math.max(...heights);
          colorLow = low; colorHigh = high;
          for (const h of heights) {
            const color = new THREE.Color().setHSL(0.48 - 0.35 * (h - low) / (high - low || 1), 0.48, 0.49);
            vertexColors.push(color.r, color.g, color.b);
          }
          const geometry = new THREE.BufferGeometry();
          geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertexPositions, 3));
          geometry.setAttribute('color', new THREE.Float32BufferAttribute(vertexColors, 3));
          geometry.setIndex(indices);
          geometry.computeVertexNormals();
          surfaceGeometry = geometry;
          object.add(new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ vertexColors: true, side: THREE.DoubleSide, roughness: 0.7, metalness: 0 })));
          if (result.options?.box_ratios) object.add(new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ color: '#31595f', wireframe: true, transparent: true, opacity: 0.14 })));
        }
        const box = new THREE.Box3().setFromObject(object);
        if (box.isEmpty()) throw new Error(t("三维绘图没有有效的实数采样点"));
        if (surfaceGeometry && result.options?.range) { box.min.y = result.options.range[0]; box.max.y = result.options.range[1]; }
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        const extent = Math.max(size.x, size.y, size.z, 0.001);
        object.scale.setScalar(4 / extent);
        const ratios = result.options?.box_ratios;
        if (ratios) {
          const unit = 4 / Math.max(...ratios);
          object.scale.set(unit*ratios[0]/(size.x || 1), unit*ratios[2]/(size.y || 1), unit*ratios[1]/(size.z || 1));
        }
        object.position.copy(center).multiply(object.scale).negate();
        const displaySize = size.clone().multiply(object.scale);
        scene.add(object);
        scene.add(new THREE.HemisphereLight(0xffffff, 0x607078, 2.3));
        const light = new THREE.DirectionalLight(0xffffff, 2.5);
        light.position.set(3, 6, 4); scene.add(light);
        const grid = new THREE.GridHelper(5, 10, '#c0cbd0', '#e0e7ea');
        grid.position.y = -displaySize.y / 2 - 0.1; scene.add(grid);
        const axes = new THREE.AxesHelper(2.7); axes.position.copy(grid.position); scene.add(axes);
        const fitDistance = () => {
          const vertical = camera.fov*Math.PI/180, horizontal = 2*Math.atan(Math.tan(vertical/2)*camera.aspect);
          return Math.max(displaySize.length()/2, 0.1)/Math.sin(Math.min(vertical,horizontal)/2)*1.1;
        };
        const reset = () => { camera.position.set(1,0.8,1).normalize().multiplyScalar(fitDistance()); controls.target.set(0,0,0); controls.update(); };
        reset(); resetRef.current = reset;
        updateRef.current = next => {
          if (!surfaceGeometry || next?.plot_type !== 'surface' || !next.x || !next.y || next.x.length !== result.x?.length || next.y.length !== result.y?.length) return;
          const positions = surfaceGeometry.getAttribute('position') as import('three').BufferAttribute;
          const shades = surfaceGeometry.getAttribute('color') as import('three').BufferAttribute;
          const count = next.x.length, rows = next.y.length, finite: boolean[] = [], triangles: number[] = [];
          const color = new THREE.Color();
          for (let j=0;j<rows;j++) for (let i=0;i<count;i++) {
            const index=j*count+i, value=next.z![j][i];
            finite.push(value !== null);
            positions.setXYZ(index,next.x[i],value ?? 0,-next.y[j]);
            color.setHSL(0.48-0.35*((value ?? colorLow)-colorLow)/(colorHigh-colorLow || 1),0.48,0.49);
            shades.setXYZ(index,color.r,color.g,color.b);
          }
          for (let j=0;j<rows-1;j++) for (let i=0;i<count-1;i++) {
            const a=j*count+i,b=a+1,c=a+count,d=c+1;
            if ([a,b,c].every(k=>finite[k])) triangles.push(a,c,b);
            if ([b,c,d].every(k=>finite[k])) triangles.push(b,c,d);
          }
          positions.needsUpdate=true; shades.needsUpdate=true;
          surfaceGeometry.setIndex(triangles); surfaceGeometry.computeVertexNormals(); surfaceGeometry.computeBoundingSphere();
        };
        setReady(value => value+1);
        exportRef.current = () => {
          renderer.render(scene, camera);
          const link = document.createElement('a'); link.download = 'calix-plot.png'; link.href = renderer.domElement.toDataURL('image/png'); link.click();
        };
        const resize = new ResizeObserver(() => {
          const { width, height } = element.getBoundingClientRect();
          if (!width || !height) return;
          renderer.setSize(width, height); camera.aspect = width / height; camera.updateProjectionMatrix(); reset();
        }); resize.observe(element);
        let frame = 0;
        const render = () => { controls.update(); renderer.render(scene, camera); frame = requestAnimationFrame(render); }; render();
        dispose = () => {
          updateRef.current = () => {};
          cancelAnimationFrame(frame); resize.disconnect(); controls.dispose(); releaseWheel();
          const geometries = new Set<import('three').BufferGeometry>();
          object.traverse(item => { const mesh = item as import('three').Mesh; if (mesh.geometry) geometries.add(mesh.geometry); if (mesh.material) { const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material]; materials.forEach(m => m.dispose()); } });
          geometries.forEach(geometry => geometry.dispose());
          grid.geometry.dispose(); (grid.material as import('three').Material).dispose(); axes.geometry.dispose();
          window.removeEventListener('calix-theme-change', recolor); renderer.dispose(); renderer.domElement.remove();
        };
      } else {
        const Plotly = (await import('plotly.js-cartesian-dist-min')).default;
        if (cancelled || !host.current) return;
        const element = host.current;
        const releaseWheel = activatePlotWheel(element);
        const traces: Record<string, unknown>[] = result.plot_type === 'curve' ? result.traces!.map((trace, i) => ({ ...trace, type: trace.style === 'bars' ? 'bar' : 'scatter', mode: trace.style === 'markers' ? 'markers' : 'lines', connectgaps: false, marker: { color: trace.color || (result.title === 'Graphics' ? '#c24e62' : colors[i % colors.length]), size: result.title === 'Graphics' ? 12 : 7 }, line: { color: trace.color || colors[i % colors.length], width: trace.width ?? 2.3 } }))
          : [{ type: result.plot_type === 'contour' ? 'contour' : 'heatmap', x: result.x, y: result.y, z: result.z, colorscale: [[0, '#173f54'], [0.35, '#218b8e'], [0.7, '#a5d3b2'], [1, '#f3d578']], contours: { coloring: 'lines' }, line: { width: 1.5 } }];
        if(result.plot_type==='density' && result.traces)traces.push(...result.traces.map(trace=>({type:'scatter',x:trace.x,y:trace.y,name:trace.name,mode:'lines',connectgaps:false,line:{color:'#273f50',width:1.1},showlegend:false,hoverinfo:'skip'})));
        if (trajectory) {
          traces[0].line = { color: '#bacdd0', width: 1.5 };
          traces.push({ type: 'scatter', x: [], y: [], mode: 'lines', line: { color: colors[0], width: 2.5 }, showlegend: false });
          traces.push({ type: 'scatter', x: [], y: [], mode: 'markers', marker: { color: colors[1], size: 11, line: { color: '#fff', width: 1.5 } }, showlegend: false });
        }
        const layout = { autosize: true, margin: { l: 54, r: 25, t: 20, b: 44 }, paper_bgcolor: plotPalette().background, plot_bgcolor: plotPalette().background, font: { family: 'Segoe UI, Microsoft YaHei, sans-serif', size: 12, color: plotPalette().text }, xaxis: { title: { text: result.axes[0] || 'x' }, gridcolor: plotPalette().grid, zerolinecolor: '#a5b2b9', automargin: true, range: result.options?.x_range }, yaxis: { title: { text: result.axes[1] || 'y' }, gridcolor: plotPalette().grid, zerolinecolor: '#a5b2b9', range: result.options?.range, automargin: true, scaleanchor: result.options?.equal_aspect ? 'x' : undefined, scaleratio: 1 }, showlegend: result.options?.legend !== false && !trajectory && result.traces && result.traces.length > 1, legend: { orientation: 'h', y: 1.12 } };
        const recolor = () => { const palette = plotPalette(); void Plotly.relayout(element, { paper_bgcolor: palette.background, plot_bgcolor: palette.background, 'font.color': palette.text, 'xaxis.gridcolor': palette.grid, 'yaxis.gridcolor': palette.grid }); };
        window.addEventListener('calix-theme-change', recolor);
        await Plotly.newPlot(element, traces, layout, { responsive: true, displayModeBar: false, scrollZoom: true });
        if (cancelled) { releaseWheel(); Plotly.purge(element); return; }
        resetRef.current = () => Plotly.relayout(element, { 'xaxis.autorange': true, 'yaxis.autorange': true });
        updateRef.current = (next, position) => {
          if (trajectory && position !== undefined) {
            const trace = result.traces![0];
            const index = Math.max(0, Math.min(trace.x.length - 1, position));
            void Plotly.restyle(element, { x: [trace.x.slice(0, index + 1), [trace.x[index]]], y: [trace.y.slice(0, index + 1), [trace.y[index]]] }, [1, 2]);
          } else if (next?.traces) {
            void Plotly.restyle(element, { x: next.traces.map(t => t.x), y: next.traces.map(t => t.y) });
          }
        };
        setReady(value => value + 1);
        exportRef.current = () => Plotly.downloadImage(element, { format: 'png', filename: 'calix-plot', width: 1400, height: 900 });
        const resize = new ResizeObserver(() => {
          if (cancelled || !element.isConnected || !element.clientWidth || !element.clientHeight) return;
          void Plotly.Plots.resize(element).catch((error: unknown) => {
            if (!cancelled && element.isConnected && element.clientWidth && element.clientHeight) setError(String(error));
          });
        }); resize.observe(element);
        dispose = () => { releaseWheel(); updateRef.current = () => {}; resize.disconnect(); window.removeEventListener('calix-theme-change', recolor); Plotly.purge(element); };
      }
    })().catch(err => { if (!cancelled) setError(String(err)); });
    return () => { cancelled = true; dispose(); };
  }, [result, is3d, trajectory]);

  useEffect(() => { updateRef.current(frame, cursor); }, [frame, cursor, ready]);

  return <div className="plot-output">
    <div className="plot-tools"><span>{result.title}</span><div><button title={t("重置视图")} onClick={() => resetRef.current()}><RotateCcw size={15} /></button><button title={t("导出 PNG")} onClick={() => exportRef.current()}><Download size={15} /></button></div></div>
    {error ? <p className="error-message">{error}</p> : <div ref={host} className="plot-canvas" />}
    {is3d && <div className="plot-axis-labels">x · {result.axes[0] || 'x'}　y · {result.axes[1] || 'y'}　z · {result.axes[2] || 'f(x,y)'}</div>}
  </div>;
}
