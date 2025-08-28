document.addEventListener('DOMContentLoaded', function(){
  var form = document.getElementById('toolForm');
  var modal = document.getElementById('interModal');
  if(form && modal){
    form.addEventListener('submit', function(){ modal.style.display = 'flex'; });
  }
});
