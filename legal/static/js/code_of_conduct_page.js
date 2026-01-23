(function() {
    const consentBanner = document.getElementById('consent-banner');
    const contentEnd = document.getElementById('page-content-end');
    const consentCheckbox = document.getElementById('consent-checkbox');
    const submitBtn = document.getElementById('submit-btn');
    const consentLabelRead = document.getElementById('consent-label-read');
    const consentLabelUnread = document.getElementById('consent-label-unread');

    let hasScrolledToEnd = false;

    function checkScrollPosition() {
        if (hasScrolledToEnd) return;

        const bannerHeight = consentBanner ? consentBanner.offsetHeight : 0;
        const rect = contentEnd.getBoundingClientRect();
        const windowHeight = window.innerHeight;

        if (rect.top + bannerHeight <= windowHeight) {
            hasScrolledToEnd = true;
            enableCheckbox();
            window.removeEventListener('scroll', checkScrollPosition);
        }
    }

    function enableCheckbox() {
        consentLabelUnread.style.display = 'none';
        consentLabelRead.style.display = 'inline';
        consentCheckbox.disabled = false;
    }

    function updateSubmitButton() {
        submitBtn.disabled = !consentCheckbox.checked;
    }

    consentCheckbox.addEventListener('change', updateSubmitButton);

    window.addEventListener('scroll', checkScrollPosition);

    checkScrollPosition();
})();
