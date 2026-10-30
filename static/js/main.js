/**
 * MEDTRACK - MODERN HEALTHCARE PLATFORM CLIENT JAVASCRIPT
 * Dual-theme management, interactive auth tabs, live search/filtering,
 * password toggle, and mobile sidebar navigation.
 */

(function () {
    'use strict';

    // =========================================================
    // 1. THEME MANAGEMENT (Dual Theme: Light / Dark)
    // =========================================================
    const THEME_KEY = 'medtrack_theme';

    function initTheme() {
        const savedTheme = localStorage.getItem(THEME_KEY);
        const systemPrefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        const currentTheme = savedTheme || (systemPrefersDark ? 'dark' : 'light');
        document.documentElement.setAttribute('data-theme', currentTheme);
        updateThemeToggleIcons(currentTheme);
    }

    function toggleTheme() {
        const current = document.documentElement.getAttribute('data-theme') || 'light';
        const next = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem(THEME_KEY, next);
        updateThemeToggleIcons(next);
    }

    function updateThemeToggleIcons(theme) {
        const buttons = document.querySelectorAll('.theme-toggle-btn');
        buttons.forEach(btn => {
            const isDark = theme === 'dark';
            btn.setAttribute('aria-label', isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode');
            btn.setAttribute('title', isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode');
            const iconSun = btn.querySelector('.theme-icon-sun');
            const iconMoon = btn.querySelector('.theme-icon-moon');
            const label = btn.querySelector('.theme-label');
            if (iconSun && iconMoon) {
                if (isDark) {
                    iconSun.style.display = 'inline-block';
                    iconMoon.style.display = 'none';
                } else {
                    iconSun.style.display = 'none';
                    iconMoon.style.display = 'inline-block';
                }
            }
            if (label) {
                label.textContent = isDark ? 'Light' : 'Dark';
            }
        });
    }

    // Run theme immediately
    initTheme();

    document.addEventListener('DOMContentLoaded', () => {
        // Bind theme toggle buttons
        const toggleButtons = document.querySelectorAll('.theme-toggle-btn');
        toggleButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                toggleTheme();
            });
        });

        // =====================================================
        // 2. MOBILE SIDEBAR TOGGLE
        // =====================================================
        const sidebar = document.querySelector('.sidebar');
        const sidebarToggle = document.querySelector('.mobile-sidebar-toggle');
        const sidebarOverlay = document.querySelector('.sidebar-overlay');

        if (sidebarToggle && sidebar) {
            sidebarToggle.addEventListener('click', () => {
                sidebar.classList.toggle('open');
                if (sidebarOverlay) sidebarOverlay.classList.toggle('active');
            });
        }

        if (sidebarOverlay && sidebar) {
            sidebarOverlay.addEventListener('click', () => {
                sidebar.classList.remove('open');
                sidebarOverlay.classList.remove('active');
            });
        }

        // =====================================================
        // 3. PASSWORD VISIBILITY TOGGLE
        // =====================================================
        const passwordToggles = document.querySelectorAll('.password-toggle-btn');
        passwordToggles.forEach(toggle => {
            toggle.addEventListener('click', function () {
                const targetId = this.getAttribute('data-target') || 'password';
                const input = document.getElementById(targetId);
                if (!input) return;

                const isPassword = input.getAttribute('type') === 'password';
                input.setAttribute('type', isPassword ? 'text' : 'password');

                const eyeOpen = this.querySelector('.eye-open');
                const eyeClosed = this.querySelector('.eye-closed');
                if (eyeOpen && eyeClosed) {
                    eyeOpen.style.display = isPassword ? 'none' : 'inline-block';
                    eyeClosed.style.display = isPassword ? 'inline-block' : 'none';
                }
            });
        });

        // =====================================================
        // 4. INTERACTIVE ONBOARDING ROLE SELECTION CARDS
        // =====================================================
        const roleCards = document.querySelectorAll('.role-select-card');
        const roleSelect = document.getElementById('role');

        if (roleCards.length && roleSelect) {
            // Sync initial selection
            const currentVal = roleSelect.value;
            roleCards.forEach(card => {
                const cardRole = card.getAttribute('data-role');
                if (cardRole === currentVal) {
                    card.classList.add('selected');
                } else {
                    card.classList.remove('selected');
                }

                card.addEventListener('click', () => {
                    const selectedRole = card.getAttribute('data-role');
                    roleSelect.value = selectedRole;
                    roleCards.forEach(c => c.classList.remove('selected'));
                    card.classList.add('selected');
                });
            });

            roleSelect.addEventListener('change', () => {
                const val = roleSelect.value;
                roleCards.forEach(card => {
                    if (card.getAttribute('data-role') === val) {
                        card.classList.add('selected');
                    } else {
                        card.classList.remove('selected');
                    }
                });
            });
        }

        // =====================================================
        // 5. LIVE SEARCH & STATUS FILTERING FOR DASHBOARDS
        // =====================================================
        const searchInput = document.getElementById('table-search-input');
        const filterChips = document.querySelectorAll('.filter-chip');
        const searchableCards = document.querySelectorAll('.searchable-item');

        function applyFilters() {
            const query = (searchInput ? searchInput.value : '').toLowerCase().trim();
            const activeChip = document.querySelector('.filter-chip.active');
            const statusFilter = activeChip ? activeChip.getAttribute('data-filter') : 'all';

            let visibleCount = 0;
            searchableCards.forEach(card => {
                const text = card.textContent.toLowerCase();
                const cardStatus = (card.getAttribute('data-status') || '').toLowerCase();

                const matchesQuery = !query || text.includes(query);
                const matchesStatus = statusFilter === 'all' || cardStatus === statusFilter.toLowerCase();

                if (matchesQuery && matchesStatus) {
                    card.style.display = '';
                    visibleCount++;
                } else {
                    card.style.display = 'none';
                }
            });

            const noResultsElem = document.getElementById('no-search-results');
            if (noResultsElem) {
                noResultsElem.style.display = (visibleCount === 0 && searchableCards.length > 0) ? 'block' : 'none';
            }
        }

        if (searchInput) {
            searchInput.addEventListener('input', applyFilters);
        }

        filterChips.forEach(chip => {
            chip.addEventListener('click', () => {
                filterChips.forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
                applyFilters();
            });
        });

        // =====================================================
        // 6. GREETING HELPER BASED ON TIME OF DAY
        // =====================================================
        const greetingSpan = document.getElementById('dynamic-greeting');
        if (greetingSpan) {
            const hour = new Date().getHours();
            let greeting = 'Good morning';
            if (hour >= 12 && hour < 17) {
                greeting = 'Good afternoon';
            } else if (hour >= 17) {
                greeting = 'Good evening';
            }
            greetingSpan.textContent = greeting;
        }

        // =====================================================
        // 7. PRINT MEDICAL RECORD TRIGGER
        // =====================================================
        const printBtn = document.getElementById('print-records-btn');
        if (printBtn) {
            printBtn.addEventListener('click', (e) => {
                e.preventDefault();
                window.print();
            });
        }
    });
})();

