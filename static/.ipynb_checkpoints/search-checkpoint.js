console.log("search.js loaded ✅");

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
}

// Improved remove handlers with better error handling and debugging
function attachRemoveHandlers() {
  // Remove any existing event listeners to prevent duplicates
  const existingForms = document.querySelectorAll('.remove-item-form');
  console.log(`Found ${existingForms.length} remove forms in DOM`);

  existingForms.forEach((form, index) => {
    // Remove any existing listeners by cloning the element
    const newForm = form.cloneNode(true);
    form.parentNode.replaceChild(newForm, form);
    
    console.log(`Attaching listener to remove form ${index}`);
    
    newForm.addEventListener('submit', async function(evt) {
      evt.preventDefault();
      evt.stopPropagation();
      
      console.log('Remove form submitted via AJAX');
      
      const li = this.closest('div'); // Changed from 'li' to 'div' to match your HTML structure
      const formData = new FormData(this);
      const index = formData.get('index');
      
      console.log('Item index to remove:', index);
      
      // Show loading state
      const submitBtn = this.querySelector('button[type="submit"]');
      const originalText = submitBtn.textContent;
      submitBtn.textContent = 'Removing...';
      submitBtn.disabled = true;

      try {
        console.log('Sending AJAX request to /api/remove_item');
        const resp = await fetch('/api/remove_item', {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
          },
          body: JSON.stringify({ index: index })
        });

        console.log('Response status:', resp.status);

        if (!resp.ok) {
          const errorText = await resp.text();
          console.log('Error response:', errorText);
          throw new Error(`HTTP ${resp.status}: ${errorText}`);
        }

        const data = await resp.json();
        console.log('Remove response:', data);

        if (data.success) {
          // Remove the item from DOM
          li.remove();

          // Update totals
          const totals = data.total;
          if (totals) {
            document.getElementById('total-calories').textContent = totals.calories || 0;
            document.getElementById('total-protein').textContent = totals.protein || 0;
            document.getElementById('total-carbs').textContent = totals.carbs || 0;
            document.getElementById('total-fat').textContent = totals.fat || 0;
            document.getElementById('total-sugar').textContent = totals.sugar || 0;
          }

          // If no items left, hide the meal section or reload to clean up UI
          if (data.remaining_items === 0) {
            console.log('No items remaining, will reload page to clean up UI');
            window.location.reload();
          }
        } else {
          throw new Error('Server returned success: false');
        }
      } catch (error) {
        console.error('Error removing item:', error);
        // Restore button state
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
        // Fallback to page reload
        alert('Error removing item. The page will reload.');
        window.location.reload();
      }
    });
  });
}

// Enhanced initialization with better timing
function initialize() {
  console.log('Initializing meal builder...');
  initSearchTool();
  attachRemoveHandlers();
}

// Multiple initialization strategies to ensure it works
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initialize);
} else {
  // DOM already loaded
  initialize();
}

// Also initialize after any potential dynamic content loads
window.addEventListener('load', () => {
  console.log('Window loaded, re-checking for remove handlers...');
  attachRemoveHandlers();
});