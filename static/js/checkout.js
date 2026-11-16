(function(){
 const form=document.getElementById('demo-payment-form'); if(!form)return;
 const radio=form.querySelectorAll('input[name="payment_method"]');
 const panels={card:document.getElementById('card-panel'),qr:document.getElementById('qr-panel')};
 function sync(){const selected=form.querySelector('input[name="payment_method"]:checked').value;
  Object.keys(panels).forEach(k=>panels[k].hidden=k!==selected);}
 radio.forEach(r=>r.addEventListener('change',sync));sync();
 const countdown=document.querySelector('.countdown-panel'),clock=document.getElementById('checkout-clock');
 const expires=Date.parse(countdown.dataset.deadline);let expired=false;
 function tick(){const ms=expires-Date.now();if(ms<=0){clock.textContent=countdown.dataset.expiredText;countdown.classList.add('expired');
  form.querySelector('button[type="submit"]').disabled=true;expired=true;return;}
  const secs=Math.ceil(ms/1000);clock.textContent=String(Math.floor(secs/60)).padStart(2,'0')+':'+String(secs%60).padStart(2,'0');}
 tick();setInterval(()=>{if(!expired)tick();},1000);
})();