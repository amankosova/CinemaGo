document.querySelectorAll(".toast").forEach(function (toast) {
  setTimeout(function () {
    toast.style.transition = "opacity 0.4s";
    toast.style.opacity = "0";
    setTimeout(function () { toast.remove(); }, 400);
  }, 5000);
});


// Accessible ticket modal: a button opens a single ticket's QR and details.
document.addEventListener("click", function (event) {
  const ticketButton = event.target.closest("[data-ticket-qr-open]");
  if (ticketButton) {
    const dialog = document.getElementById(ticketButton.dataset.ticketQrOpen);
    if (dialog && typeof dialog.showModal === "function") dialog.showModal();
    return;
  }
  const trailerButton = event.target.closest("[data-trailer-open]");
  if (trailerButton) {
    const dialog = document.getElementById("movie-trailer-dialog");
    if (!dialog || typeof dialog.showModal !== "function") return;
    const frame = dialog.querySelector(".cg-video-frame");
    const id = frame && frame.dataset.youtubeId;
    if (!id || !/^[A-Za-z0-9_-]{11}$/.test(id)) return;
    frame.replaceChildren();
    const iframe = document.createElement("iframe");
    iframe.title = "Movie trailer";
    iframe.allow = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share";
    iframe.allowFullscreen = true;
    iframe.referrerPolicy = "strict-origin-when-cross-origin";
    iframe.src = "https://www.youtube-nocookie.com/embed/" + id + "?autoplay=1&rel=0";
    frame.appendChild(iframe);
    dialog.showModal();
    return;
  }
  const closeButton = event.target.closest("[data-dialog-close]");
  if (closeButton) {
    const dialog = closeButton.closest("dialog");
    if (dialog) dialog.close();
  }
});
// Closing a trailer stops video playback, including with Escape.
document.addEventListener("close", function (event) {
  if (event.target.id === "movie-trailer-dialog") {
    const frame = event.target.querySelector(".cg-video-frame");
    if (frame) frame.replaceChildren();
  }
}, true);
// Outside-click close for native dialogs (Escape also works by default).
document.addEventListener("click", function (event) {
  if (event.target.matches("dialog.cg-modal")) {
    const d = event.target;
    const bounds = d.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) d.close();
  }
});
