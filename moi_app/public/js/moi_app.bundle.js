import './../css/moi_app.css';
import "./workflow_progress.js";

const translate = () => {
    root_element.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        console.log(key);
        if (!key) return;
        console.log(__(key));
        el.textContent = __(key);
    });
};

