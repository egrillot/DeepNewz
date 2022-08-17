function display_feed(data){
    var to_display =  '<label>'
                            +'<input type="button" class="refresh" style="display: none;"/>'
                            +'<div id="refresh" style="animation: 0.4s ease-out 0s pop;" onclick="refresh()">'+ data['feed_message'] +'</div>'
                        +'</label>'
                        +'<div class="boxes">'

    for (let i = 0; i < data['cache'].length; i++){

        var summary = data['cache'][i][1]
        var sentiment = data['cache'][i][2]
        var date = data['cache'][i][3]
        var title = data['cache'][i][4]

        to_display +=  '<div class="box s-'+ sentiment +'" style="animation: 0.4s ease-out 0s pop;">'
                            +'<h2>'+ title +'</h2>'
                            +'<p>'+ summary +'}</p>'
                        +'<div class="date">Created at '+ date +'</div>'
                    +'</div>'          
    }
    to_display += +'</div>';
    $(".feed").html(to_display);
}

function display_loading(){
    $(".feed").html('<div class="loader"><div class="inner one"></div><div class="inner two"></div><div class="inner three"></div></div>')
}

$('.positive').click(function(e){
    e.preventDefault();
    $.get( "/change_params", {sentiment: 'positive'}, function( data ) {
        console.log(JSON.stringify(data));
        if (data['pos'] == "1"){
            $(".radio-pos").prop("checked", true);
        }else{
            $(".radio-pos").prop("checked", false);
        }
        display_feed(data);
    } );
})

function refresh(){
    display_loading();
    $.get("/load_feed", function(data){
        display_feed(data);
    });
}

$('.neutral').click(function(e){
    e.preventDefault();
    $.get( "/change_params", {sentiment: 'neutral'}, function( data ) {
        console.log(JSON.stringify(data));
        if (data['neu'] == "1"){
            $(".radio-neu").prop("checked", true);
        }else{
            $(".radio-neu").prop("checked", false);
        }
        display_feed(data);
      } );
})

$('.negative').click(function(e){
    e.preventDefault();
    $.get( "/change_params", {sentiment: 'negative'}, function( data ) {
        console.log(JSON.stringify(data));
        if (data['neg'] == "1"){
            $(".radio-neg").prop("checked", true);
        }else{
            $(".radio-neg").prop("checked", false);
        }
        display_feed(data);
      } );
})

$('#France').click(function(e){
    e.preventDefault();
    $.get( "/change_params", {country: 'France'}, function( data ){
        console.log(JSON.stringify(data));
        $('.radio-France').prop("checked", true);
        $('.radio-' + data['b']).prop("checked", false);
        display_feed(data);
    })
})

$('#Japan').click(function(e){
    e.preventDefault();
    $.get( "/change_params", {country: 'japan'}, function( data ){
        console.log(JSON.stringify(data));
        $('.radio-japan').prop("checked", true);
        $('.radio-' + data['b']).prop("checked", false);
        display_feed(data);
    })
})

$('#UK').click(function(e){
    e.preventDefault();
    $.get( "/change_params", {country: 'UK'}, function( data ){
        console.log(JSON.stringify(data));
        $('.radio-UK').prop("checked", true);
        $('.radio-' + data['b']).prop("checked", false);
        display_feed(data);
    });
})

$('#USA').click(function(e){
    e.preventDefault();
    $.get( "/change_params", {country: 'USA'}, function( data ){
        console.log(JSON.stringify(data));
        $('.radio-USA').prop("checked", true);
        $('.radio-' + data['b']).prop("checked", false);
        display_feed(data);
    });
})
