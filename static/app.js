document.querySelectorAll('[data-confirm]').forEach(form => {
  form.addEventListener('submit', event => {
    if (!window.confirm(form.dataset.confirm || 'Are you sure?')) event.preventDefault();
  });
});
document.querySelectorAll('.flash-close').forEach(button => {
  button.addEventListener('click', () => button.closest('.flash').remove());
});