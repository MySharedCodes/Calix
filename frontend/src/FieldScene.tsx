import { plotPalette } from './themes';
import { activatePlotWheel } from './plotInteraction';
import { useEffect, useRef, useState } from 'react';
import { Download, Pause, Play, RotateCcw } from 'lucide-react';
import type { PlotResult } from './types';
import { t } from './i18n';
import './field-scene.css';

const volumeVertex=`out vec3 point; void main(){point=position+0.5;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`;
const volumeFragment=`
precision highp float;
uniform vec3 eye, low, high, bodies[5];
uniform float masses[5], epsilon, opacity;
uniform int bodyCount;
uniform vec2 colorRange;
in vec3 point;
out vec4 outputColor;
void main(){
 vec3 origin=eye+0.5, direction=normalize(point-origin);
 vec3 a=(vec3(0.0)-origin)/direction,b=(vec3(1.0)-origin)/direction;
 vec3 n=min(a,b),f=max(a,b);
 float start=max(0.0,max(max(n.x,n.y),n.z)),stop=min(min(f.x,f.y),f.z);
 if(stop<=start)discard;
 float stepSize=(stop-start)/160.0;
 vec4 sum=vec4(0.0);
 for(int i=0;i<160;i++){
   vec3 coordinate=origin+direction*(start+(float(i)+0.5)*stepSize);
   vec3 p=mix(low,high,coordinate);
   float potential=0.0;
   for(int j=0;j<5;j++){if(j>=bodyCount)break;vec3 delta=p-bodies[j];potential-=masses[j]/sqrt(dot(delta,delta)+epsilon*epsilon);}
   float weight=clamp((colorRange.y-potential)/(colorRange.y-colorRange.x),0.0,1.0);
   float alpha=1.0-exp(-opacity*pow(weight,2.1)*stepSize*30.0);
   vec3 color=mix(vec3(0.08,0.54,0.63),vec3(0.98,0.36,0.14),weight);
   sum.rgb+=(1.0-sum.a)*alpha*color;sum.a+=(1.0-sum.a)*alpha;
   if(sum.a>0.995)break;
 }
 outputColor=sum;
}`;
const sliceVertex=`in vec3 samplePoint;out vec3 point;void main(){point=samplePoint;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`;
const sliceFragment=`precision highp float;precision highp sampler3D;uniform sampler3D field;uniform float opacity;in vec3 point;out vec4 outputColor;void main(){float v=texture(field,point).r;vec3 color=mix(vec3(0.07,0.41,0.68),vec3(0.99,0.46,0.12),v);outputColor=vec4(color,1.0-exp(-opacity*2.5*v));}`;

export function FieldScene({result}:{result:PlotResult}){
  const host=useRef<HTMLDivElement>(null),reset=useRef(()=>{}),download=useRef(()=>{});
  const playback=useRef({position:0,playing:false,opacity:result.field_kind==='gravity'?2.2:0.7});
  const [position,setPosition]=useState(0),[playing,setPlaying]=useState(false),[opacity,setOpacity]=useState(playback.current.opacity),[error,setError]=useState('');
  const gravity=result.field_kind==='gravity';
  const times=result.times!,time=times[0]+position*(times[times.length-1]-times[0]);
  useEffect(()=>{
    let cancelled=false,dispose=()=>{};
    (async()=>{
      const THREE=await import('three');const {OrbitControls}=await import('three/addons/controls/OrbitControls.js');
      const [{Line2},{LineGeometry},{LineMaterial}]=await Promise.all([import('three/addons/lines/Line2.js'),import('three/addons/lines/LineGeometry.js'),import('three/addons/lines/LineMaterial.js')]);
      if(cancelled||!host.current)return;
      const element=host.current,renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});
      const releaseWheel=activatePlotWheel(element);
      renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.setClearColor(plotPalette().background);
      const recolor = () => renderer.setClearColor(plotPalette().background); window.addEventListener('calix-theme-change', recolor);
      renderer.domElement.setAttribute('aria-label',gravity?'Many-body gravitational potential volume':'Coils, magnetic field lines and translucent slices');element.appendChild(renderer.domElement);
      const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(38,1,0.01,100),controls=new OrbitControls(camera,renderer.domElement);
      controls.enableDamping=true;controls.minDistance=2;controls.maxDistance=30;
      const object=new THREE.Group();scene.add(object);
      const vector=(p:number[])=>new THREE.Vector3(p[0],p[2],-p[1]);
      const bounds=result.bounds!,low=bounds.map(b=>b[0]),high=bounds.map(b=>b[1]),extent=Math.max(...bounds.map(b=>b[1]-b[0]));
      const center=low.map((v,i)=>(v+high[i])/2),textures:import('three').Texture[]=[],shaders:import('three').ShaderMaterial[]=[];
      let cloud:import('three').Mesh|undefined,volumeMaterial:import('three').ShaderMaterial|undefined;
      const trajectoryMaterials:InstanceType<typeof LineMaterial>[]=[];
      const line=(points:number[][],color:string,opacity=1,thick=false)=>{
        if(thick){
          const geometry=new LineGeometry();geometry.setPositions(points.flatMap(p=>vector(p).toArray()));
          const material=new LineMaterial({color,linewidth:2.6,depthTest:false});trajectoryMaterials.push(material);
          const path=new Line2(geometry,material);path.renderOrder=2;object.add(path);return;
        }
        const geometry=new THREE.BufferGeometry().setFromPoints(points.map(vector));
        const path=new THREE.Line(geometry,new THREE.LineBasicMaterial({color,transparent:opacity<1,opacity,depthTest:false}));path.renderOrder=2;object.add(path);
      };
      if(gravity){
        volumeMaterial=new THREE.ShaderMaterial({glslVersion:THREE.GLSL3,vertexShader:volumeVertex,fragmentShader:volumeFragment,side:THREE.BackSide,transparent:true,depthWrite:false,premultipliedAlpha:true,
          uniforms:{eye:{value:new THREE.Vector3()},low:{value:new THREE.Vector3(...low as [number,number,number])},high:{value:new THREE.Vector3(...high as [number,number,number])},
            bodies:{value:Array.from({length:5},()=>new THREE.Vector3())},masses:{value:[...result.masses!,...Array(5-result.masses!.length).fill(0)]},bodyCount:{value:result.masses!.length},epsilon:{value:result.softening},opacity:{value:playback.current.opacity},colorRange:{value:new THREE.Vector2(...result.color_range! as [number,number])}}});
        shaders.push(volumeMaterial);cloud=new THREE.Mesh(new THREE.BoxGeometry(1,1,1),volumeMaterial);cloud.rotation.x=-Math.PI/2;
        cloud.scale.set(...bounds.map(b=>b[1]-b[0]) as [number,number,number]);cloud.position.copy(vector(center));object.add(cloud);
      }else{
        const texture=new THREE.Data3DTexture(Uint8Array.from(atob(result.volume!),c=>c.charCodeAt(0)),result.size!,result.size!,result.size!);
        texture.format=THREE.RedFormat;texture.type=THREE.UnsignedByteType;texture.minFilter=texture.magFilter=THREE.LinearFilter;texture.unpackAlignment=1;texture.needsUpdate=true;textures.push(texture);
        for(const axis of [0,1]){
          const other=[0,1,2].filter(v=>v!==axis),points:number[][]=[];
          for(const [a,b] of [[0,0],[1,0],[1,1],[0,1]]){const p=[0,0,0];p[other[0]]=bounds[other[0]][a];p[other[1]]=bounds[other[1]][b];points.push(p);}
          const geometry=new THREE.BufferGeometry().setFromPoints(points.map(vector));geometry.setIndex([0,1,2,0,2,3]);
          geometry.setAttribute('samplePoint',new THREE.Float32BufferAttribute(points.flatMap(p=>p.map((v,i)=>(v-low[i])/(high[i]-low[i]))),3));
          const material=new THREE.ShaderMaterial({glslVersion:THREE.GLSL3,vertexShader:sliceVertex,fragmentShader:sliceFragment,side:THREE.DoubleSide,transparent:true,depthWrite:false,uniforms:{field:{value:texture},opacity:{value:playback.current.opacity}}});
          shaders.push(material);object.add(new THREE.Mesh(geometry,material));
        }
        result.coils!.forEach(z=>{const ring=new THREE.Mesh(new THREE.TorusGeometry(1,0.014,10,160),new THREE.MeshStandardMaterial({color:'#b97135',roughness:0.5}));ring.rotation.x=-Math.PI/2;ring.position.y=z;object.add(ring);});
        result.field_lines!.forEach(points=>line(points,'#668c94',0.38));
      }
      result.paths!.forEach((path,i)=>line(path,result.colors![i],1,!gravity));
      const balls=result.paths!.map((_,i)=>{
        const ball=new THREE.Mesh(new THREE.SphereGeometry(extent*(gravity?0.014:0.01),20,16),new THREE.MeshStandardMaterial({color:result.colors![i],depthTest:false}));ball.renderOrder=3;object.add(ball);return ball;
      });
      const edges=new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(high[0]-low[0],high[2]-low[2],high[1]-low[1])),new THREE.LineBasicMaterial({color:'#bdcdd4',transparent:true,opacity:0.38}));edges.position.copy(vector(center));object.add(edges);
      object.scale.setScalar(3.5/extent);object.position.copy(vector(center)).multiplyScalar(-3.5/extent);
      scene.add(new THREE.HemisphereLight(0xffffff,0x6c7b83,2.3));const light=new THREE.DirectionalLight(0xffffff,2.5);light.position.set(3,5,4);scene.add(light);
      reset.current=()=>{const angle=Math.min(camera.fov*Math.PI/180,2*Math.atan(Math.tan(camera.fov*Math.PI/360)*camera.aspect));camera.position.set(1,0.65,1.3).normalize().multiplyScalar(2.6/Math.sin(angle/2));controls.target.set(0,0,0);controls.update();};
      const draw=()=>{
        const cursor=playback.current.position*(times.length-1),index=Math.min(times.length-2,Math.floor(cursor)),fraction=cursor-index;
        balls.forEach((ball,i)=>{const a=result.paths![i][index],b=result.paths![i][index+1],p=a.map((v,j)=>v+(b[j]-v)*fraction);ball.position.copy(vector(p));if(volumeMaterial)volumeMaterial.uniforms.bodies.value[i].set(p[0],p[1],p[2]);});
        shaders.forEach(material=>material.uniforms.opacity.value=playback.current.opacity);
        if(volumeMaterial&&cloud){cloud.updateWorldMatrix(true,false);volumeMaterial.uniforms.eye.value.copy(cloud.worldToLocal(camera.position.clone()));}
        controls.update();renderer.render(scene,camera);
      };
      download.current=()=>{draw();const link=document.createElement('a');link.download=gravity?'calix-gravity-potential.png':'calix-magnetic-field.png';link.href=renderer.domElement.toDataURL('image/png');link.click();};
      const resize=new ResizeObserver(()=>{const {width,height}=element.getBoundingClientRect();if(width&&height){renderer.setSize(width,height);trajectoryMaterials.forEach(material=>material.resolution.set(width,height));camera.aspect=width/height;camera.updateProjectionMatrix();reset.current();}});resize.observe(element);
      let visible=true,handle=0,previous=performance.now(),lastUI=0;
      const observer=new IntersectionObserver(entries=>visible=entries[0].isIntersecting);observer.observe(element);
      const render=(now:number)=>{
        if(visible&&playback.current.playing&&!document.hidden){playback.current.position=Math.min(1,playback.current.position+Math.min(now-previous,100)/8000);if(now-lastUI>32){setPosition(playback.current.position);lastUI=now;}if(playback.current.position===1){playback.current.playing=false;setPlaying(false);setPosition(1);}}
        previous=now;if(visible)draw();handle=requestAnimationFrame(render);
      };handle=requestAnimationFrame(render);
      dispose=()=>{releaseWheel();cancelAnimationFrame(handle);resize.disconnect();observer.disconnect();controls.dispose();const geometries=new Set<import('three').BufferGeometry>(),materials=new Set<import('three').Material>();scene.traverse(item=>{const mesh=item as import('three').Mesh;if(mesh.geometry)geometries.add(mesh.geometry);if(mesh.material)(Array.isArray(mesh.material)?mesh.material:[mesh.material]).forEach(m=>materials.add(m));});geometries.forEach(g=>g.dispose());materials.forEach(m=>m.dispose());textures.forEach(v=>v.dispose());window.removeEventListener('calix-theme-change', recolor); renderer.dispose();renderer.domElement.remove();};
    })().catch(error=>{if(!cancelled)setError(String(error));});
    return()=>{cancelled=true;dispose();};
  },[result,gravity]);
  return <div className={`plot-output field-scene ${gravity?'gravity-scene':'magnetic-scene'}`}>
    <div className="plot-tools"><span>{result.title}</span><div><button title={t('重置视图')} onClick={()=>reset.current()}><RotateCcw size={15}/></button><button title={t('导出 PNG')} onClick={()=>download.current()}><Download size={15}/></button></div></div>
    {error?<p className="error-message">{error}</p>:<div className="plot-canvas" ref={host}/>}
    <div className="scene-legend">{!gravity&&<><span><i style={{background:'#b97135'}}/>{t('同轴线圈')}</span><span><i style={{background:'#668c94'}}/>{t('磁感线')}</span></>}{result.labels!.map((label,i)=><span key={i}><i style={{background:result.colors![i]}}/>{label}</span>)}</div>
    <div className={`field-color-scale ${gravity?'gravity-scale':''}`}><span>{gravity?'Φ = U / m_test':'|B| / B0'}</span><output>{result.color_range![0].toFixed(2)}</output><i/><output>{result.color_range![1].toFixed(2)}</output>{!gravity&&<span>log(1 + |B| / B0)</span>}</div>
    <div className="animation-controls"><button className="icon-button" title={t(playing?'暂停动画':'播放动画')} onClick={()=>{if(playback.current.position>=1){playback.current.position=0;setPosition(0);}playback.current.playing=!playing;setPlaying(!playing);}}>{playing?<Pause size={17}/>:<Play size={17}/>}</button><button className="icon-button" title={t('重置动画')} onClick={()=>{playback.current.position=0;playback.current.playing=false;setPosition(0);setPlaying(false);}}><RotateCcw size={16}/></button><input aria-label={t('动画进度')} type="range" min="0" max="1000" value={Math.round(position*1000)} onChange={e=>{const p=Number(e.target.value)/1000;playback.current.position=p;playback.current.playing=false;setPosition(p);setPlaying(false);}}/><output>t = {time.toFixed(3)}</output></div>
    <label className="cloud-opacity">{t('不透明度')}<input aria-label={t('不透明度')} type="range" min="0.1" max="4" step="0.1" value={opacity} onChange={e=>{const value=Number(e.target.value);playback.current.opacity=value;setOpacity(value);}}/><output>{opacity.toFixed(1)}</output></label>
    <div className="scene-scale">{result.axes.map((a,i)=>`${a}: ${result.bounds![i][0].toFixed(2)} … ${result.bounds![i][1].toFixed(2)}`).join(' · ')}</div>
  </div>;
}
