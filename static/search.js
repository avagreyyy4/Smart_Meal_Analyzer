document.addEventListener('DOMContentLoaded', function() {
  const queryInput = document.getElementById('query');
  const suggestionsBox = document.getElementById('custom-suggestions');
  const fdcInput = document.getElementById('fdc_id');
  const foodNameInput = document.getElementById('food_name');

  queryInput.addEventListener('input', async () => {
    const q = queryInput.value.trim();
    if (q.length < 2) {
      suggestionsBox.style.display = 'none';
      return;
    }

    try {
      const resp = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
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
      console.error(e);
    }
  });

  document.addEventListener('click', e => {
    if (!suggestionsBox.contains(e.target) && e.target !== queryInput) {
      suggestionsBox.style.display = 'none';
    }
  });
});

