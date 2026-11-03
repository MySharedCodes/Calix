import { t } from './i18n';
import { useEffect, useMemo, useState } from 'react';
import { Pause, Play, RotateCcw } from 'lucide-react';
import { Plot } from './Plot';
import type { AnimationResult } from './types';

export function Animation({ result }: { result: AnimationResult }) {
  const [position, setPosition] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [loop, setLoop] = useState(false);
  const last = result.values.length - 1;
  const index = Math.min(last, Math.round(position * last));
  const plot = useMemo(() => {
    if (!result.frames) return result.plot;
    if (result.plot.plot_type === 'surface') {
      const heights = result.frames.flatMap(frame => frame.z!.flat().filter((value): value is number => value !== null));
      const low = heights.reduce((a, b) => Math.min(a, b), Infinity), high = heights.reduce((a, b) => Math.max(a, b), -Infinity);
      return { ...result.plot, options: { ...result.plot.options, range: result.plot.options?.range || [low, high] } };
    }
    const ys = result.frames.flatMap(frame => frame.traces!.flatMap(trace => trace.y.filter((y): y is number => y !== null)));
    const low = ys.reduce((a, b) => Math.min(a, b), Infinity), high = ys.reduce((a, b) => Math.max(a, b), -Infinity);
    if (!Number.isFinite(low) || !Number.isFinite(high)) return result.plot;
    const pad = (high - low || 1) * 0.08;
    const xs = result.frames.flatMap(frame => frame.traces!.flatMap(trace => trace.x.filter((x): x is number => x !== null)));
    const left = xs.reduce((a, b) => Math.min(a, b), Infinity), right = xs.reduce((a, b) => Math.max(a, b), -Infinity);
    const xpad = (right - left || 1) * 0.08;
    return { ...result.plot, options: { ...result.plot.options, range: [low - pad, high + pad], x_range: [left - xpad, right + xpad] } };
  }, [result]);

  useEffect(() => { setPosition(0); setPlaying(false); }, [result]);
  useEffect(() => {
    if (!playing) return;
    let handle = 0;
    let previous = performance.now();
    let accumulated = 0;
    const tick = (now: number) => {
      accumulated += document.hidden ? 0 : Math.min(now - previous, 100);
      previous = now;
      if (accumulated >= 1000 / 30) {
        const step = accumulated / 6000 * speed;
        accumulated = 0;
        setPosition(current => current + step >= 1 ? (loop ? (current + step) % 1 : 1) : current + step);
      }
      handle = requestAnimationFrame(tick);
    };
    handle = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(handle);
  }, [playing, speed, loop]);
  useEffect(() => { if (position >= 1 && !loop) setPlaying(false); }, [position, loop]);

  return <div className="animation-output">
    <Plot result={plot} trajectory={result.animation_type === 'trajectory'} cursor={index} frame={result.frames?.[index]} />
    <div className="animation-controls">
      <button className="icon-button" title={playing ? t("暂停动画") : t("播放动画")} onClick={() => { if (position >= 1) setPosition(0); setPlaying(!playing); }}>{playing ? <Pause size={17} /> : <Play size={17} />}</button>
      <button className="icon-button" title={t("重置动画")} onClick={() => { setPosition(0); setPlaying(false); }}><RotateCcw size={16} /></button>
      <input aria-label={t("动画进度")} type="range" min="0" max={last} step="1" value={index} onChange={event => { setPlaying(false); setPosition(Number(event.target.value) / last); }} />
      <output aria-label={t("动画参数")}>{result.parameter} = {result.values[index].toFixed(2)}</output>
      <select aria-label={t("动画速度")} value={speed} onChange={event => setSpeed(Number(event.target.value))}>{[0.25, 0.5, 1, 2, 4].map(value => <option key={value} value={value}>{value}×</option>)}</select>
      <label><input type="checkbox" checked={loop} onChange={event => setLoop(event.target.checked)} />{t("循环")}</label>
    </div>
  </div>;
}
