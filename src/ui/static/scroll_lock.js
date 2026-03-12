(function() {
    if (window.__scrollLockApplied) return;
    window.__scrollLockApplied = true;

    // 사용자가 직접 스크롤할 때만 허용 플래그
    let userInitiated = false;
    ['wheel', 'touchmove', 'touchstart', 'keydown', 'mousedown'].forEach(evt => {
        window.addEventListener(evt, () => {
            userInitiated = true;
            setTimeout(() => { userInitiated = false; }, 300);
        }, { capture: true, passive: true });
    });

    // window.scrollTo / window.scroll 차단
    const _scrollTo = window.scrollTo.bind(window);
    window.scrollTo = function(...args) {
        if (userInitiated) _scrollTo(...args);
    };
    window.scroll = function(...args) {
        if (userInitiated) _scrollTo(...args);
    };

    // Element.scrollIntoView 차단
    Element.prototype.scrollIntoView = function() {};

    // ScrollToBottom 버튼 제거
    new MutationObserver(function() {
        document.querySelectorAll('[data-testid="ScrollToBottomContainer"]')
            .forEach(el => el.remove());
    }).observe(document.body, { childList: true, subtree: true });
})();
