var lotto_form  = document.querySelector(".lotto_form");
var lotto_input = lotto_form.querySelector(".lotto_input");
var html_num_list = document.querySelector(".html_num_list");


let num_list = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45];

function insert_number(){
    lotto_form.addEventListener("submit", handleSubmitMakeNum);
}


function handleSubmitMakeNum(e){
    e.preventDefault();
    make_num();    
}

function make_num(){
    var k = 1
    while(k<9){
        var new_num_list = [];
        for(i=0; i<6; i++){
            while(new_num_list.length < 6){
                var get_number = Math.ceil(Math.random()*45);
                var check_number = num_list.includes(get_number);
            if(check_number === true){
                var index = num_list.indexOf(get_number);  // env에 설명
                num_list.splice(index, 1);
                new_num_list.push(get_number);
            } else if(num_list.length === 0){
                break;
            } else{
                continue;
            }
        };

        }        
        maked_num = new_num_list.sort(function(a, b){return a-b});
        show_num(k, maked_num);
        k++;
    }
    insert_line();
    num_list = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45];
}

function show_num(k, maked_num){
    var div = document.createElement("div");
    var span = document.createElement("span");
    span.innerText = `${k<8? `게임 ${k} : ${maked_num}` : `남은 숫자 : ${maked_num}`}`
    div.appendChild(span);
    html_num_list.appendChild(div);
}

function insert_line(){
    var div = document.createElement("div")
    var span = document.createElement("span");
    span.innerText = '-----------------------------'
    div.appendChild(span);
    html_num_list.appendChild(div);
}

insert_number();
