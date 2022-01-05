//toggle button

function serialComm(){
  // Get the checkbox
  var checkBox = document.getElementById("serial_com_toggle");
  // Get the output text
  var text = document.getElementById("serial_com_input").value;

  // If the checkbox is checked, display the output text
  if (checkBox.checked == true){
    console.log("puerto:",text,"ON");
  } else {
     console.log("puerto:",text,"OFF");
  }

  $.ajax({
    url: "/laser",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('serial_com_apply').value,
      'input': document.getElementById("serial_com_input").value
    },
    dataType:"json",
    success: function (data) {
    }
  });
}