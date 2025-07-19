function initSearchTool() {
  const queryInput = document.getElementById('query');
  const suggestionsBox = document.getElementById('custom-suggestions');
  const fdcInput = document.getElementById('fdc_id');
  const foodNameInput = document.getElementById('food_name');

  let debounceTimer = null;
  let controller = null;

  queryInput.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    const q = queryInput.value.trim();
    if (q.length < 2) {
      suggestionsBox.style.display = 'none';
      return;
    }

    debounceTimer = setTimeout(async () => {
      if (controller) controller.abort();
      controller = new AbortController();
      try {
        const resp = await fetch(`/api/search?q=${encodeURIComponent(q)}`, {
          signal: controller.signal,
          headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        if (!resp.ok) return;
        const data = await resp.json();
        suggestionsBox.innerHTML = '';
        data.forEach(item => {
          const li = document.createElement('li');
          li.textContent = item.description;
          li.dataset.fdc = item.fdcId;
          li.style.padding = '6px 8px';
          li.style.cursor = 'pointer';
          li.addEventListener('click', () => {
            queryInput.value = item.description;
            fdcInput.value = item.fdcId;
            foodNameInput.value = item.description;
            suggestionsBox.style.display = 'none';
          });
          suggestionsBox.appendChild(li);
        });
        suggestionsBox.style.display = data.length ? 'block' : 'none';
      } catch (e) {
        if (e.name !== 'AbortError') {
          console.error(e);
        }
      }
    }, 300);
  });

  document.addEventListener('click', e => {
    if (!suggestionsBox.contains(e.target) && e.target !== queryInput) {
      suggestionsBox.style.display = 'none';
    }
  });

  document.addEventListener('submit', async evt => {
    const form = evt.target.closest('.remove-item-form');
    if (!form) return; // not a remove form
    evt.preventDefault();
    const li = form.closest('li');
    const formData = new FormData(form);
    const resp = await fetch(form.action, {
      method: 'POST',
      body: formData,
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });
    if (!resp.ok) return window.location.reload();
    const data = await resp.json();
    li.remove();
    const totals = data.total;
    if (totals) {
      document.getElementById('total-calories').textContent = totals.calories;
      document.getElementById('total-protein').textContent = totals.protein;
      document.getElementById('total-carbs').textContent = totals.carbs;
      document.getElementById('total-fat').textContent = totals.fat;
      document.getElementById('total-sugar').textContent = totals.sugar;
    }
  });

}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initSearchTool);
} else {
  initSearchTool();
}

