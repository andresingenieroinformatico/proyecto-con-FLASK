function mostrarOpcionesPasajeros() {
    const tipoVehiculo = document.getElementById('tipo_vehiculo').value;
    const pasajerosBus = document.getElementById('pasajeros-bus');
    const pasajerosOtros = document.getElementById('pasajeros-otros');
    const numPasajerosBus = document.getElementById('cant_pasajeros_bus');
    const numPasajerosOtros = document.getElementById('cant_pasajeros_otros');

    // Ocultamos ambos contenedores al inicio
    pasajerosBus.style.display = 'none';
    pasajerosOtros.style.display = 'none';

    // Quitamos los atributos 'required' y 'name' de ambos campos
    numPasajerosBus.removeAttribute('required');
    numPasajerosOtros.removeAttribute('required');
    numPasajerosBus.removeAttribute('name');
    numPasajerosOtros.removeAttribute('name');

    document.getElementById('destino').addEventListener('change', function () {
        if (this.value === document.getElementById('origen').value) {
            alert('El destino no puede ser igual al origen.');
            this.value = "";
        }
    });    

    if (tipoVehiculo === 'bus') {
        pasajerosBus.style.display = 'block';
        numPasajerosBus.setAttribute('required', 'required');
        numPasajerosBus.setAttribute('name', 'cant_pasajeros');
    } else if (tipoVehiculo === 'carro_particular' || tipoVehiculo === 'taxi') {
        pasajerosOtros.style.display = 'block';
        numPasajerosOtros.setAttribute('required', 'required');
        numPasajerosOtros.setAttribute('name', 'cant_pasajeros');
    }
}
