// Capture the wheel before either plotting library can consume notebook scrolling.
export function activatePlotWheel(element: HTMLElement) {
  let active = false;
  const pointer = (event: PointerEvent) => {
    active = element.contains(event.target as Node);
    element.dataset.wheelActive = String(active);
  };
  const blur = () => { active = false; element.dataset.wheelActive = 'false'; };
  const wheel = (event: WheelEvent) => {
    if (!active || event.ctrlKey) event.stopImmediatePropagation();
  };
  element.dataset.wheelActive = 'false';
  document.addEventListener('pointerdown', pointer, true);
  window.addEventListener('blur', blur);
  element.addEventListener('wheel', wheel, { capture: true, passive: true });
  return () => {
    document.removeEventListener('pointerdown', pointer, true);
    window.removeEventListener('blur', blur);
    element.removeEventListener('wheel', wheel, true);
  };
}
