document.addEventListener("DOMContentLoaded", function () {
    const togglePassword = document.getElementById("togglePassword");
    const passwordField = document.getElementById("password");

    if (togglePassword && passwordField) {
        togglePassword.addEventListener("click", function () {
            const isPasswordHidden = passwordField.type === "password";
            const cursorPosition = passwordField.selectionStart; 

            passwordField.type = isPasswordHidden ? "text" : "password";

            passwordField.setSelectionRange(cursorPosition, cursorPosition);
            passwordField.focus();

            this.classList.toggle("fa-eye");
            this.classList.toggle("fa-eye-slash");
        });
    } else {
        console.error("No se encontraron los elementos togglePassword o password.");
    }
});
