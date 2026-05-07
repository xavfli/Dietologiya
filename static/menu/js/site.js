document.addEventListener("DOMContentLoaded", function () {
    document.body.classList.add("fx-preload");
    requestAnimationFrame(() => {
        document.body.classList.add("is-ready");
    });

    const revealElements = document.querySelectorAll(
        ".template-feature, .feature-card, .content-panel, .org-card, .inner-hero, .app-table, .about-img, .about-check, .section-header, .profile-stat-card, .profile-menu-card, .profile-calendar__summary-card, .timeline-item, .journey-item"
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

    const interactiveCards = document.querySelectorAll(
        ".template-feature, .feature-card, .org-card, .profile-stat-card, .profile-menu-card, .content-panel, .inner-hero"
    );

    interactiveCards.forEach((card) => {
        card.classList.add("fx-tilt");
        card.addEventListener("mousemove", (event) => {
            if (window.matchMedia("(max-width: 991px)").matches) {
                return;
            }
            const rect = card.getBoundingClientRect();
            const px = (event.clientX - rect.left) / rect.width;
            const py = (event.clientY - rect.top) / rect.height;
            const rotateY = (px - 0.5) * 7;
            const rotateX = (0.5 - py) * 7;
            card.style.setProperty("--fx-rotate-x", `${rotateX}deg`);
            card.style.setProperty("--fx-rotate-y", `${rotateY}deg`);
        });
        card.addEventListener("mouseleave", () => {
            card.style.setProperty("--fx-rotate-x", "0deg");
            card.style.setProperty("--fx-rotate-y", "0deg");
        });
    });

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
