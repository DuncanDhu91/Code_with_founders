// Quality Gates Data
const qualityGates = [
    {
        name: "Test Execution",
        target: "100%",
        actual: "100%",
        status: "passed",
        description: "All tests must run"
    },
    {
        name: "Pass Rate",
        target: "≥95%",
        actual: "97.5%",
        status: "passed",
        description: "Tests must pass reliably"
    },
    {
        name: "Line Coverage",
        target: "≥90%",
        actual: "96.8%",
        status: "passed",
        description: "Adequate code coverage"
    },
    {
        name: "Critical Path Coverage",
        target: "100%",
        actual: "100%",
        status: "passed",
        description: "currency_agent.py fully covered"
    },
    {
        name: "P0 Bugs",
        target: "0",
        actual: "0",
        status: "passed",
        description: "No critical bugs allowed"
    },
    {
        name: "P1 Bugs",
        target: "≤3",
        actual: "1",
        status: "passed",
        description: "Limited high-priority bugs"
    },
    {
        name: "CI Execution Time",
        target: "<5 min",
        actual: "3.5 min",
        status: "passed",
        description: "Fast feedback loop"
    }
];

// Populate Quality Gates
function populateQualityGates() {
    const container = document.getElementById('qualityGates');

    qualityGates.forEach(gate => {
        const gateElement = document.createElement('div');
        gateElement.className = 'flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:shadow-md transition';

        const statusIcon = gate.status === 'passed'
            ? '<i class="fas fa-check-circle text-green-500 text-2xl"></i>'
            : '<i class="fas fa-times-circle text-red-500 text-2xl"></i>';

        const statusBadge = gate.status === 'passed'
            ? '<span class="px-3 py-1 bg-green-100 text-green-800 text-sm font-semibold rounded-full">PASS</span>'
            : '<span class="px-3 py-1 bg-red-100 text-red-800 text-sm font-semibold rounded-full">FAIL</span>';

        gateElement.innerHTML = `
            <div class="flex items-center space-x-4 flex-1">
                ${statusIcon}
                <div class="flex-1">
                    <h3 class="font-semibold text-gray-800">${gate.name}</h3>
                    <p class="text-sm text-gray-600">${gate.description}</p>
                </div>
            </div>
            <div class="text-right">
                <div class="flex items-center space-x-4 mb-2">
                    <div>
                        <p class="text-xs text-gray-500">Target</p>
                        <p class="font-semibold text-gray-700">${gate.target}</p>
                    </div>
                    <div>
                        <p class="text-xs text-gray-500">Actual</p>
                        <p class="font-semibold text-gray-900">${gate.actual}</p>
                    </div>
                </div>
                ${statusBadge}
            </div>
        `;

        container.appendChild(gateElement);
    });
}

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    populateQualityGates();

    // Add smooth scroll
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Add animation to stats on scroll
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '0';
                entry.target.style.transform = 'translateY(20px)';
                setTimeout(() => {
                    entry.target.style.transition = 'all 0.6s ease-out';
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }, 100);
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Observe elements for animation
    document.querySelectorAll('.bg-white').forEach(el => {
        observer.observe(el);
    });
});

// Add click handler for GitHub links
document.querySelectorAll('a[target="_blank"]').forEach(link => {
    link.addEventListener('click', function(e) {
        // Track analytics if needed
        console.log('External link clicked:', this.href);
    });
});
