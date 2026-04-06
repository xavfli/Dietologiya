document.addEventListener("DOMContentLoaded", function () {
    const revealElements = document.querySelectorAll(
        ".template-feature, .feature-card, .content-panel, .org-card, .inner-hero, .app-table, .about-img, .about-check, .section-header"
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
        return;
    }

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

    revealElements.forEach((element) => {
        element.classList.add("reveal-on-scroll");
        observer.observe(element);
    });

    const calendars = document.querySelectorAll("[data-profile-calendar]");
    calendars.forEach((calendar) => {
        const triggers = calendar.querySelectorAll("[data-day-trigger]");
        const panels = calendar.querySelectorAll("[data-day-panel]");

        const activateDay = (dayId) => {
            triggers.forEach((trigger) => {
                const isActive = trigger.dataset.dayTrigger === dayId;
                trigger.classList.toggle("is-active", isActive);
                trigger.setAttribute("aria-selected", isActive ? "true" : "false");
            });

            panels.forEach((panel) => {
                const isActive = panel.dataset.dayPanel === dayId;
                panel.classList.toggle("d-none", !isActive);
            });
        };

        triggers.forEach((trigger) => {
            trigger.addEventListener("click", () => activateDay(trigger.dataset.dayTrigger));
        });
    });
});
