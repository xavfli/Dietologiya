from django.shortcuts import render


ERROR_PAGE_CONTENT = {
    400: {
        "title": "Noto'g'ri so'rov",
        "text": "So'rovda xatolik bor. Sahifani yangilab ko'ring yoki bosh sahifaga qayting.",
    },
    403: {
        "title": "Ruxsat yo'q",
        "text": "Bu sahifani ko'rish uchun sizda yetarli ruxsat yo'q.",
    },
    404: {
        "title": "Sahifa topilmadi",
        "text": "Manzil o'zgargan yoki noto'g'ri kiritilgan bo'lishi mumkin.",
    },
    500: {
        "title": "Server xatosi",
        "text": "Ichki xatolik yuz berdi. Iltimos, birozdan keyin qayta urinib ko'ring.",
    },
}


def error_page(request, exception=None, status_code=500):
    content = ERROR_PAGE_CONTENT[status_code]
    return render(
        request,
        "menu/error.html",
        {
            "status_code": status_code,
            "error_title": content["title"],
            "error_text": content["text"],
        },
        status=status_code,
    )


def bad_request(request, exception):
    return error_page(request, exception, 400)


def permission_denied(request, exception):
    return error_page(request, exception, 403)


def page_not_found(request, exception):
    return error_page(request, exception, 404)


def server_error(request):
    return error_page(request, status_code=500)
