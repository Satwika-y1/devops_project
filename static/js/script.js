// Auto-hide success messages after 4 seconds (server-side validation is the real safety net).
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".auto-dismiss.alert-success").forEach(function (el) {
    setTimeout(function () {
      if (window.bootstrap) { bootstrap.Alert.getOrCreateInstance(el).close(); }
    }, 4000);
  });
  // Submit the filter form immediately when the category changes.
  var select = document.getElementById("category-select");
  if (select) { select.addEventListener("change", function () { select.form.submit(); }); }
});
