document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });
});

const style = document.createElement('style');
style.textContent = `
    @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

const registroForm = document.querySelector('form[action*="registro"]');
if (registroForm) {
    registroForm.addEventListener('submit', function(e) {
        const password = document.getElementById('password').value;
        const confirmarPassword = document.getElementById('confirmar_password').value;
        
        if (password !== confirmarPassword) {
            e.preventDefault();
            alert('Las contraseñas no coinciden');
        }
        
        if (password.length < 6) {
            e.preventDefault();
            alert('La contraseña debe tener al menos 6 caracteres');
        }
    });
}

const userButton = document.querySelector('.user-button');
if (userButton) {
    userButton.addEventListener('click', function(e) {
        e.stopPropagation();
        const dropdown = document.querySelector('.user-dropdown');
        dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
    });
    
    document.addEventListener('click', function() {
        const dropdown = document.querySelector('.user-dropdown');
        if (dropdown) dropdown.style.display = 'none';
    });
}