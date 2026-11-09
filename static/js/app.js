document.querySelectorAll(".toast").forEach(function (toast) {
  setTimeout(function () {
    toast.style.transition = "opacity 0.4s";
    toast.style.opacity = "0";
    setTimeout(function () { toast.remove(); }, 400);
  }, 5000);
});
