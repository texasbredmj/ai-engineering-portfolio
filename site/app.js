// Progress is self-reported and stays in page memory; no backend calls or tokens.
const steps = Array.from(document.querySelectorAll('[data-step]'));
function updateProgress() {
  const count = steps.filter(step => step.checked).length;
  document.getElementById('progress').textContent = `${count} of 5 steps marked complete`;
}
steps.forEach(step => step.addEventListener('change', updateProgress));
document.getElementById('reset').addEventListener('click', () => {
  steps.forEach(step => { step.checked = false; });
  updateProgress();
});
