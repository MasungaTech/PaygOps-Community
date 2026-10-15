
function initMap() {
    var map = new google.maps.Map(document.getElementById('map'), {
        mapTypeId: google.maps.MapTypeId.TERRAIN,
        zoomControl: true,
        mapTypeControl: true,
        scaleControl: true,
        streetViewControl: false,
        rotateControl: false,
        fullscreenControl: true
    });

    var bounds = new google.maps.LatLngBounds();

    var infowindow = new google.maps.InfoWindow({pixelOffset: new google.maps.Size(-11, 0)});

    var markertable = [];

    for (i = 0; i < locations.length; i++) {
        var marker = new google.maps.Marker({
            position: new google.maps.LatLng(locations[i][1], locations[i][2]),
            animation: google.maps.Animation.DROP,
            map: map,
            icon: {
                url: '/static/img/map_icon_' + locations[i][3] + '.png',
                anchor: new google.maps.Point(15, 42),
                scaledSize: new google.maps.Size(30, 46)
            }
        });

        //extend the bounds to include each marker's position
        loc = new google.maps.LatLng(marker.position.lat(), marker.position.lng());
        bounds.extend(loc);

        google.maps.event.addListener(marker, 'click', (function (marker, i) {
            return function () {
                infowindow.setContent(locations[i][0]);
                infowindow.open(map, marker);
                map.panTo(marker.getPosition());
                marker.setAnimation(null);
            }
        })(marker, i));

        markertable[locations[i][4]] = marker;
    }

    //now fit the map to the newly inclusive bounds
    map.fitBounds(bounds);

    var listener = google.maps.event.addListener(map, "idle", function() {
      if (map.getZoom() > 13) map.setZoom(13);
      google.maps.event.removeListener(listener);
    });
}
