import { plotPalette } from './themes';
import { activatePlotWheel } from './plotInteraction';
import { useEffect, useRef, useState } from 'react';
import { Download, RotateCcw } from 'lucide-react';
import type { PlotResult } from './types';
import { t } from './i18n';
import './scientific-scene.css';

const vertexShader = `
out vec3 point;
void main() {
  point = position + 0.5;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}`;
const fragmentShader = `
precision highp float;
precision highp sampler3D;
uniform sampler3D density;
uniform vec3 eye;
uniform float opacity;
in vec3 point;
out vec4 outputColor;
void main() {
  vec3 origin = eye + 0.5;
  vec3 direction = normalize(point-origin);
  vec3 nearPlane = (vec3(0.0)-origin)/direction;
  vec3 farPlane = (vec3(1.0)-origin)/direction;
  vec3 lower = min(nearPlane,farPlane), upper = max(nearPlane,farPlane);
  float enter = max(max(lower.x,lower.y),lower.z);
  float leave = min(min(upper.x,upper.y),upper.z);
  enter = max(enter,0.0);
  if (leave<=enter) discard;
  float stepSize = (leave-enter)/192.0;
  vec4 accumulated = vec4(0.0);
  for (int i=0;i<192;i++) {
    vec3 coordinate = origin+direction*(enter+(float(i)+0.5)*stepSize);
    float encoded = texture(density,coordinate).r;
    float amount = pow(encoded,0.9);
    float alpha = 1.0-exp(-opacity*amount*stepSize*13.0);
    vec3 color = mix(vec3(0.04,0.49,0.65),vec3(0.98,0.64,0.20),pow(encoded,1.6));
    accumulated.rgb += (1.0-accumulated.a)*alpha*color;
    accumulated.a += (1.0-accumulated.a)*alpha;
    if (accumulated.a>0.995) break;
  }
  outputColor = accumulated;
}`;

export function ScientificScene({ result }: { result: PlotResult }) {
  const host = useRef<HTMLDivElement>(null);
  const reset = useRef(() => {}), download = useRef(() => {});
  const opacityRef = useRef(1.8);
  const [opacity, setOpacity] = useState(1.8);
  const [error, setError] = useState('');
  const volume = result.plot_type === 'volume';
  const legend = [...new Map(result.primitives?.filter(p => p.label).map(p => [p.label, p.color])).entries()];

  useEffect(() => {
    let cancelled = false, dispose = () => {};
    setError('');
    (async () => {
      const THREE = await import('three');
      const { OrbitControls } = await import('three/addons/controls/OrbitControls.js');
      if (cancelled || !host.current) return;
      const element = host.current;
      const releaseWheel = activatePlotWheel(element);
      const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
      renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
      renderer.setClearColor(plotPalette().background);
      const recolor = () => renderer.setClearColor(plotPalette().background); window.addEventListener('calix-theme-change', recolor);
      renderer.domElement.setAttribute('aria-label', volume ? '3D probability cloud' : result.options?.wireframe ? '3D finite element mesh' : '3D scientific scene');
      element.appendChild(renderer.domElement);
      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(38, 1, 0.01, 100);
      const controls = new OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true; controls.minDistance = 2; controls.maxDistance = 30;
      const object = new THREE.Group(); scene.add(object);
      const textures: import('three').Texture[] = [];
      let material: import('three').ShaderMaterial | undefined;
      let cloud: import('three').Mesh | undefined;
      let planar = false;
      const vector = (p: number[]) => new THREE.Vector3(p[0],p[2],-p[1]);

      if (volume) {
        const bytes = Uint8Array.from(atob(result.volume!), c => c.charCodeAt(0));
        const texture = new THREE.Data3DTexture(bytes,result.size!,result.size!,result.size!);
        texture.format = THREE.RedFormat; texture.type = THREE.UnsignedByteType;
        texture.minFilter = texture.magFilter = THREE.LinearFilter;
        texture.unpackAlignment = 1; texture.needsUpdate = true; textures.push(texture);
        material = new THREE.ShaderMaterial({
          glslVersion: THREE.GLSL3, vertexShader, fragmentShader,
          uniforms: { density: { value: texture }, eye: { value: new THREE.Vector3() }, opacity: { value: opacityRef.current } },
          side: THREE.BackSide, transparent: true, depthWrite: false, premultipliedAlpha: true,
        });
        cloud = new THREE.Mesh(new THREE.BoxGeometry(1,1,1),material);
        // Texture coordinates retain physical x,y,z; rotate the whole cube to keep z vertical.
        cloud.rotation.x = -Math.PI/2;
        const lengths = result.bounds!.map(b => b[1]-b[0]), extent = Math.max(...lengths);
        cloud.scale.set(...lengths.map(length => length/extent*3) as [number,number,number]);
        object.add(cloud);
        const edges = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(1,1,1)),new THREE.LineBasicMaterial({ color:'#c5d2d8',transparent:true,opacity:0.6 }));
        edges.rotation.copy(cloud.rotation); edges.scale.copy(cloud.scale); object.add(edges);
      } else {
        const points = result.primitives!.flatMap(p => p.points);
        const box = new THREE.Box3().setFromPoints(points.map(vector));
        const extent = Math.max(box.getSize(new THREE.Vector3()).length(),0.01);
        planar = box.getSize(new THREE.Vector3()).y < extent*0.01;
        const triangles: number[] = [], shades: number[] = [];
        const lineGroups = new Map<string, import('three').Vector3[]>();
        for (const primitive of result.primitives!) {
          const vertices = primitive.points.map(vector);
          if (primitive.type === 'triangle') {
            vertices.forEach((v,i) => { const shade=new THREE.Color(primitive.colors?.[i] || primitive.color);triangles.push(v.x,v.y,v.z); shades.push(shade.r,shade.g,shade.b); });
          } else if (primitive.type === 'arrow') {
            const direction = vertices[1].clone().sub(vertices[0]), length = direction.length();
            if (length>0) object.add(new THREE.ArrowHelper(direction.normalize(),vertices[0],length,primitive.color,Math.min(length*0.35,extent*0.035),Math.min(length*0.2,extent*0.018)));
          } else if (primitive.type === 'point') {
            for (const vertex of vertices) {
              const dot = new THREE.Mesh(new THREE.SphereGeometry(extent*0.012,16,12),new THREE.MeshStandardMaterial({color:primitive.color}));
              dot.position.copy(vertex); object.add(dot);
            }
          } else if (result.options?.wireframe || result.title.startsWith('Bridge ')) {
            const lines = lineGroups.get(primitive.color) || [];
            for (let i=1;i<vertices.length;i++) lines.push(vertices[i-1],vertices[i]);
            lineGroups.set(primitive.color,lines);
          } else {
            const path = new THREE.CurvePath<import('three').Vector3>();
            for (let i=1;i<vertices.length;i++) if (vertices[i].distanceToSquared(vertices[i-1])>1e-16) path.add(new THREE.LineCurve3(vertices[i-1],vertices[i]));
            if (path.curves.length) object.add(new THREE.Mesh(new THREE.TubeGeometry(path,Math.min(vertices.length*2,2000),extent*0.004,7,false),new THREE.MeshStandardMaterial({color:primitive.color,roughness:0.55})));
          }
        }
        for (const [color,vertices] of lineGroups) object.add(new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(vertices),new THREE.LineBasicMaterial({color})));
        if (triangles.length) {
          const geometry = new THREE.BufferGeometry();
          geometry.setAttribute('position',new THREE.Float32BufferAttribute(triangles,3));
          geometry.setAttribute('color',new THREE.Float32BufferAttribute(shades,3)); geometry.computeVertexNormals();
          object.add(new THREE.Mesh(geometry,new THREE.MeshBasicMaterial({vertexColors:true,side:THREE.DoubleSide,polygonOffset:true,polygonOffsetFactor:1,polygonOffsetUnits:1})));
        }
        object.scale.setScalar(3.6/extent); object.position.copy(box.getCenter(new THREE.Vector3())).multiplyScalar(-3.6/extent);
      }
      scene.add(new THREE.HemisphereLight(0xffffff,0x6d7e85,2.2));
      const light = new THREE.DirectionalLight(0xffffff,2); light.position.set(4,6,3); scene.add(light);
      const axes = new THREE.AxesHelper(0.8); axes.rotation.x=-Math.PI/2; axes.position.set(-1.8,-1.7,1.8); scene.add(axes);
      const caption = (text: string, position: import('three').Vector3) => {
        const canvas = document.createElement('canvas'); canvas.width = 128; canvas.height = 64;
        const context = canvas.getContext('2d')!;
        context.fillStyle='#394b55'; context.font='32px Segoe UI'; context.textAlign='center'; context.fillText(text,64,42);
        const texture = new THREE.CanvasTexture(canvas); textures.push(texture);
        const sprite = new THREE.Sprite(new THREE.SpriteMaterial({map:texture,depthTest:false}));
        sprite.position.copy(position); sprite.scale.set(0.35,0.175,1); scene.add(sprite);
      };
      caption('x',axes.position.clone().add(new THREE.Vector3(1,0,0)));
      caption('z',axes.position.clone().add(new THREE.Vector3(0,1,0)));
      caption('y',axes.position.clone().add(new THREE.Vector3(0,0,-1)));
      const origin = new THREE.Vector3();
      reset.current = () => {
        const tangent = Math.tan(camera.fov*Math.PI/360);
        const direction = (planar ? new THREE.Vector3(0,1,0.0001) : new THREE.Vector3(1,0.75,1.3)).normalize();
        const right = new THREE.Vector3(0,1,0).cross(direction).normalize();
        const up = direction.clone().cross(right).normalize();
        const box = new THREE.Box3().setFromObject(object);
        const corners: import('three').Vector3[] = [];
        if (volume) {
          for (const x of [box.min.x,box.max.x]) for (const y of [box.min.y,box.max.y]) for (const z of [box.min.z,box.max.z]) corners.push(new THREE.Vector3(x,y,z));
        } else {
          object.updateWorldMatrix(true,false);
          result.primitives!.forEach(p=>p.points.forEach(point=>corners.push(object.localToWorld(vector(point)))));
        }
        let distance = 0;
        for (const corner of corners) {
          distance = Math.max(distance,corner.dot(direction)+Math.abs(corner.dot(up))/tangent,corner.dot(direction)+Math.abs(corner.dot(right))/(tangent*camera.aspect));
        }
        camera.position.copy(direction).multiplyScalar(Math.max(2.1,distance*1.08));
        controls.target.copy(origin); controls.update();
      };
      const draw = () => {
        controls.update();
        if (material && cloud) {
          cloud.updateWorldMatrix(true,false);
          material.uniforms.eye.value.copy(cloud.worldToLocal(camera.position.clone()));
          material.uniforms.opacity.value = opacityRef.current;
        }
        renderer.render(scene,camera);
      };
      download.current = () => { draw(); const link=document.createElement('a'); link.download=volume?'calix-probability-cloud.png':'calix-3d-scene.png'; link.href=renderer.domElement.toDataURL('image/png'); link.click(); };
      const resize = new ResizeObserver(() => {
        const {width,height} = element.getBoundingClientRect();
        if (!width || !height) return;
        renderer.setSize(width,height); camera.aspect=width/height; camera.updateProjectionMatrix(); reset.current();
      }); resize.observe(element);
      let visible = true, frame = 0;
      const visibility = new IntersectionObserver(entries => { visible=entries[0].isIntersecting; }); visibility.observe(element);
      const render = () => { if (visible) draw(); frame=requestAnimationFrame(render); }; render();
      dispose = () => {
        releaseWheel(); cancelAnimationFrame(frame); resize.disconnect(); visibility.disconnect(); controls.dispose();
        const geometries = new Set<import('three').BufferGeometry>(), materials = new Set<import('three').Material>();
        scene.traverse(item => { const mesh=item as import('three').Mesh; if(mesh.geometry) geometries.add(mesh.geometry); if(mesh.material) (Array.isArray(mesh.material)?mesh.material:[mesh.material]).forEach(m=>materials.add(m)); });
        geometries.forEach(g=>g.dispose()); materials.forEach(m=>m.dispose()); textures.forEach(texture=>texture.dispose());
        window.removeEventListener('calix-theme-change', recolor); renderer.dispose(); renderer.domElement.remove(); reset.current=()=>{}; download.current=()=>{};
      };
    })().catch(error => { if (!cancelled) setError(String(error)); });
    return () => { cancelled=true; dispose(); };
  }, [result, volume]);

  return <div className={`plot-output scientific-scene ${volume?'probability-cloud':''}`}>
    <div className="plot-tools"><span>{result.title}</span><div><button title={t('重置视图')} onClick={()=>reset.current()}><RotateCcw size={15}/></button><button title={t('导出 PNG')} onClick={()=>download.current()}><Download size={15}/></button></div></div>
    {error?<p className="error-message">{error}</p>:<div className="plot-canvas" ref={host}/>}
    {volume?<>
      <label className="cloud-opacity">{t('不透明度')}<input aria-label={t('不透明度')} type="range" min="0.3" max="5" step="0.1" value={opacity} onChange={event=>{const value=Number(event.target.value);opacityRef.current=value;setOpacity(value);}}/><output>{opacity.toFixed(1)}</output></label>
      <div className="scene-scale">{result.axes.map((axis,i)=>`${axis}: ${result.bounds![i][0]} … ${result.bounds![i][1]}`).join(' · ')}<br/>ρmax = {result.density_max!.toPrecision(4)} · {t('透明度映射')} ∝ (ρ / ρmax)<sup>0.45</sup></div>
    </>:result.scalar_legend?<div className="scalar-legend"><span>{result.scalar_legend.label}</span><div className="scalar-scale" style={{background:`linear-gradient(to right,${result.scalar_legend.colors.join(',')})`}}/><div className="scalar-ticks">{[0,.25,.5,.75,1].map(t=>{const value=result.scalar_legend!.range[0]+t*(result.scalar_legend!.range[1]-result.scalar_legend!.range[0]);return <span key={t}>{Number(value.toPrecision(4))}</span>;})}</div></div>:<div className="scene-legend">{legend.map(([label,color])=><span key={label}><i style={{background:color}}/>{label}</span>)}</div>}
  </div>;
}
