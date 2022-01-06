//sounding.js

$('#ussdt_checkbox').click(function() {
    $('#station_number').attr('disabled', this.checked)
    $('#date_sounding').attr('disabled', this.checked)
    $('#region_sounding').attr('disabled', this.checked)
});