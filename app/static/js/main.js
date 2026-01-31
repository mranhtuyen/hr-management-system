// HR Management System - Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide flash messages after 5 seconds
    const flashMessages = document.querySelectorAll('[x-data="{ show: true }"]');
    flashMessages.forEach(function(msg) {
        setTimeout(function() {
            msg.style.display = 'none';
        }, 5000);
    });

    // Confirm dialogs
    const confirmButtons = document.querySelectorAll('[data-confirm]');
    confirmButtons.forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm');
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });

    // Form validation
    const forms = document.querySelectorAll('form[data-validate]');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;

            requiredFields.forEach(function(field) {
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add('border-red-500');
                } else {
                    field.classList.remove('border-red-500');
                }
            });

            if (!isValid) {
                e.preventDefault();
                alert('Vui long dien day du thong tin bat buoc.');
            }
        });
    });

    // Date picker defaults
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(function(input) {
        if (!input.value) {
            input.value = new Date().toISOString().split('T')[0];
        }
    });

    // Number formatting for currency inputs
    const currencyInputs = document.querySelectorAll('input[data-currency]');
    currencyInputs.forEach(function(input) {
        input.addEventListener('blur', function() {
            const value = parseFloat(this.value.replace(/,/g, ''));
            if (!isNaN(value)) {
                this.value = value.toLocaleString('vi-VN');
            }
        });

        input.addEventListener('focus', function() {
            this.value = this.value.replace(/,/g, '');
        });
    });

    // Checkbox select all
    const selectAllCheckboxes = document.querySelectorAll('[data-select-all]');
    selectAllCheckboxes.forEach(function(checkbox) {
        const targetName = checkbox.getAttribute('data-select-all');
        const targetCheckboxes = document.querySelectorAll(`input[name="${targetName}"]`);

        checkbox.addEventListener('change', function() {
            targetCheckboxes.forEach(function(cb) {
                cb.checked = checkbox.checked;
            });
        });
    });

    // Table sorting
    const sortableHeaders = document.querySelectorAll('th[data-sort]');
    sortableHeaders.forEach(function(header) {
        header.style.cursor = 'pointer';
        header.addEventListener('click', function() {
            const table = header.closest('table');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            const column = header.cellIndex;
            const type = header.getAttribute('data-sort');
            const isAsc = header.classList.contains('sort-asc');

            rows.sort(function(a, b) {
                let aVal = a.cells[column].textContent.trim();
                let bVal = b.cells[column].textContent.trim();

                if (type === 'number') {
                    aVal = parseFloat(aVal.replace(/[^0-9.-]/g, '')) || 0;
                    bVal = parseFloat(bVal.replace(/[^0-9.-]/g, '')) || 0;
                }

                if (isAsc) {
                    return aVal > bVal ? -1 : 1;
                } else {
                    return aVal > bVal ? 1 : -1;
                }
            });

            // Remove sort classes from all headers
            sortableHeaders.forEach(function(h) {
                h.classList.remove('sort-asc', 'sort-desc');
            });

            // Add sort class to current header
            header.classList.add(isAsc ? 'sort-desc' : 'sort-asc');

            // Re-append rows in new order
            rows.forEach(function(row) {
                tbody.appendChild(row);
            });
        });
    });

    // Print functionality
    const printButtons = document.querySelectorAll('[data-print]');
    printButtons.forEach(function(btn) {
        btn.addEventListener('click', function() {
            window.print();
        });
    });

    // Loading state for forms
    const submitButtons = document.querySelectorAll('form button[type="submit"]');
    submitButtons.forEach(function(btn) {
        btn.closest('form').addEventListener('submit', function() {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner inline-block mr-2"></span> Dang xu ly...';
        });
    });

    // Tooltip initialization (if using)
    const tooltips = document.querySelectorAll('[data-tooltip]');
    tooltips.forEach(function(el) {
        el.addEventListener('mouseenter', function() {
            const text = this.getAttribute('data-tooltip');
            const tooltip = document.createElement('div');
            tooltip.className = 'absolute bg-gray-800 text-white text-sm px-2 py-1 rounded -mt-8';
            tooltip.textContent = text;
            this.style.position = 'relative';
            this.appendChild(tooltip);
        });

        el.addEventListener('mouseleave', function() {
            const tooltip = this.querySelector('.absolute');
            if (tooltip) tooltip.remove();
        });
    });
});

// Utility functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('vi-VN').format(amount) + 'd';
}

function formatDate(date) {
    return new Date(date).toLocaleDateString('vi-VN');
}

function formatTime(time) {
    return time.substring(0, 5);
}

// Export functions for use in templates
window.hrUtils = {
    formatCurrency: formatCurrency,
    formatDate: formatDate,
    formatTime: formatTime
};
