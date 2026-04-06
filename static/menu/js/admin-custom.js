(function () {
    function injectProfileLink() {
        if (!window.location.pathname.startsWith("/organization-admin/")) {
            return;
        }

        const navbarList = document.querySelector("#jazzy-navbar .navbar-nav.ms-auto");
        if (!navbarList || navbarList.querySelector(".org-admin-profile-link")) {
            return;
        }

        const userDropdown = navbarList.querySelector(".nav-item.dropdown");
        if (!userDropdown) {
            return;
        }

        const linkItem = document.createElement("li");
        linkItem.className = "nav-item";
        linkItem.innerHTML = [
            '<a href="/profile/" class="nav-link org-admin-profile-link">',
            '<i class="fas fa-arrow-left"></i>',
            "<span>Profilga qaytish</span>",
            "</a>",
        ].join("");

        navbarList.insertBefore(linkItem, userDropdown);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", injectProfileLink);
        return;
    }

    injectProfileLink();
})();
