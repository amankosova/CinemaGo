(function () {
  var form = document.querySelector("[data-seat-form]");
  if (!form) return;

  var price = Number(form.dataset.price);
  var maxSeats = Number(form.dataset.max);
  var boxes = form.querySelectorAll("input[type=checkbox]");
  var chosenText = document.getElementById("chosen");
  var totalText = document.getElementById("total");
  var button = document.getElementById("continue");
  var limitText = document.getElementById("limit-note");

  function update() {
    var labels = [];
    boxes.forEach(function (box) {
      if (box.checked) labels.push(box.dataset.label);
    });
    chosenText.textContent = labels.length ? labels.join(", ") : "—";
    totalText.textContent = price * labels.length + " ₸";
    button.disabled = labels.length === 0;
    limitText.hidden = true;
  }

  boxes.forEach(function (box) {
    box.addEventListener("change", function () {
      var count = form.querySelectorAll("input[type=checkbox]:checked").length;
      if (count > maxSeats) {
        box.checked = false;
        update();
        limitText.hidden = false;
        return;
      }
      update();
    });
  });

  update();
})();
