console.log("SmartPay Loaded Successfully");

/* AUTO HIDE FLASH MESSAGE */

setTimeout(() => {

    const flash = document.querySelector('.flash-message');

    if(flash){

        flash.style.display = 'none';

    }

}, 3000);

function toggleBalance(balance){

    const balanceText =
    document.getElementById('balanceAmount');

    if(balanceText.innerText === '₹ ****'){

        balanceText.innerText =
        '₹ ' + balance;

    }

    else{

        balanceText.innerText =
        '₹ ****';

    }

}