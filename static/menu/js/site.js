document.addEventListener("DOMContentLoaded", function () {
    document.body.classList.add("fx-preload");
    requestAnimationFrame(() => {
        document.body.classList.add("is-ready");
    });

    const revealElements = document.querySelectorAll(
        ".template-feature, .feature-card, .content-panel, .org-card, .inner-hero, .app-table, .about-img, .about-check, .section-header, .profile-stat-card, .profile-menu-card, .profile-calendar__summary-card, .timeline-item, .journey-item, .live-hero-board, .brief-info-card, .dashboard-story__panel, .news-preview-card, .page-hero-copy, .page-hero-visual, .login-panel, .login-preview, .admin-preview-card, .admin-preview-board"
    );
    const navbar = document.querySelector(".site-navbar");

    const syncNavbarState = () => {
        if (!navbar) {
            return;
        }
        navbar.classList.toggle("is-scrolled", window.scrollY > 12);
    };

    syncNavbarState();
    window.addEventListener("scroll", syncNavbarState, { passive: true });

    if (!("IntersectionObserver" in window)) {
        revealElements.forEach((element) => element.classList.add("is-visible"));
    } else {
        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("is-visible");
                        observer.unobserve(entry.target);
                    }
                });
            },
            { threshold: 0.12 }
        );

        revealElements.forEach((element, index) => {
            element.classList.add("reveal-on-scroll");
            element.style.setProperty("--reveal-delay", `${Math.min(index * 40, 360)}ms`);
            observer.observe(element);
        });
    }

    const buttons = document.querySelectorAll(".btn");
    buttons.forEach((button) => {
        button.classList.add("fx-ripple-host");
        button.addEventListener("click", (event) => {
            const rect = button.getBoundingClientRect();
            const ripple = document.createElement("span");
            ripple.className = "fx-ripple";
            ripple.style.left = `${event.clientX - rect.left}px`;
            ripple.style.top = `${event.clientY - rect.top}px`;
            button.appendChild(ripple);
            window.setTimeout(() => ripple.remove(), 550);
        });
    });

    const calendars = document.querySelectorAll("[data-profile-calendar]");
    calendars.forEach((calendar) => {
        const triggers = calendar.querySelectorAll("[data-day-trigger]");
        const panels = calendar.querySelectorAll("[data-day-panel]");

        const activateDay = (dayId, updateUrl = true) => {
            let activeTrigger = null;
            triggers.forEach((trigger) => {
                const isActive = trigger.dataset.dayTrigger === dayId;
                trigger.classList.toggle("is-active", isActive);
                trigger.setAttribute("aria-selected", isActive ? "true" : "false");
                trigger.tabIndex = isActive ? 0 : -1;
                if (isActive) {
                    activeTrigger = trigger;
                }
            });

            panels.forEach((panel) => {
                const isActive = panel.dataset.dayPanel === dayId;
                panel.classList.toggle("d-none", !isActive);
                panel.hidden = !isActive;
                if (isActive) {
                    panel.classList.add("is-visible");
                }
            });

            if (updateUrl && activeTrigger && window.history.replaceState) {
                const url = new URL(window.location.href);
                url.searchParams.set("day", activeTrigger.dataset.dayDate);
                window.history.replaceState({}, "", url);
            }
        };

        triggers.forEach((trigger, index) => {
            trigger.addEventListener("click", () => activateDay(trigger.dataset.dayTrigger));
            trigger.addEventListener("keydown", (event) => {
                if (!["ArrowLeft", "ArrowRight"].includes(event.key)) {
                    return;
                }
                event.preventDefault();
                const direction = event.key === "ArrowRight" ? 1 : -1;
                const nextIndex = (index + direction + triggers.length) % triggers.length;
                const nextTrigger = triggers[nextIndex];
                activateDay(nextTrigger.dataset.dayTrigger);
                nextTrigger.focus();
            });
        });

        const initialTrigger = calendar.querySelector("[data-day-trigger].is-active") || triggers[0];
        if (initialTrigger) {
            activateDay(initialTrigger.dataset.dayTrigger, false);
        }
    });

});
