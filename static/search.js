document.addEventListener('DOMContentLoaded', function() {
  const queryInput = document.getElementById('query');
  const datalist = document.getElementById('suggestions');
  const fdcInput = document.getElementById('fdc_id');
  const foodNameInput = document.getElementById('food_name');
  if(!queryInput) return;

  queryInput.addEventListener('input', async () => {
    const q = queryInput.value.trim();
    if (q.length < 2) return;
    try {
      const resp = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
      if (!resp.ok) return;
      const data = await resp.json();
      datalist.innerHTML = '';
      data.forEach(item => {
        const opt = document.createElement('option');
        opt.value = item.description;
        opt.dataset.fdc = item.fdcId;
        datalist.appendChild(opt);
      });
    } catch(e) {
      console.error(e);
    }
  });

  queryInput.addEventListener('change', () => {
    const val = queryInput.value;
    const option = Array.from(datalist.options).find(o => o.value === val);
    if (option) {
      fdcInput.value = option.dataset.fdc;
      foodNameInput.value = option.value;
    }
  });
});
