// =============================================
// MAIN JAVASCRIPT FILE
// =============================================

// Initialize when DOM is loaded
document.addEventListener("DOMContentLoaded", function () {
  initializeNavbar();
  initializeAnimations();
  initializeSession();
  initializeFormValidations();
  initializeTheme();
});

// =============================================
// NAVBAR FUNCTIONALITY
// =============================================
function initializeNavbar() {
  const navbar = document.querySelector(".navbar");
  const mobileMenuBtn = document.querySelector(".mobile-menu-btn");
  const navbarLinks = document.querySelector(".navbar-links");

  // Navbar scroll effect
  window.addEventListener("scroll", function () {
    if (window.scrollY > 50) {
      navbar.classList.add("scrolled");
    } else {
      navbar.classList.remove("scrolled");
    }
  });

  // Mobile menu toggle
  if (mobileMenuBtn && navbarLinks) {
    mobileMenuBtn.addEventListener("click", function () {
      navbarLinks.style.display =
        navbarLinks.style.display === "flex" ? "none" : "flex";
      navbarLinks.style.flexDirection = "column";
      navbarLinks.style.position = "absolute";
      navbarLinks.style.top = "70px";
      navbarLinks.style.left = "0";
      navbarLinks.style.right = "0";
      navbarLinks.style.background = "rgba(2, 6, 23, 0.95)";
      navbarLinks.style.backdropFilter = "blur(20px)";
      navbarLinks.style.borderBottom = "1px solid var(--glass-border)";
      navbarLinks.style.padding = "20px";
      navbarLinks.style.gap = "20px";
      navbarLinks.style.zIndex = "9998";
    });
  }

  // Close mobile menu on link click
  document.querySelectorAll(".navbar-links a").forEach((link) => {
    link.addEventListener("click", function () {
      if (window.innerWidth <= 768) {
        navbarLinks.style.display = "none";
      }
    });
  });

  // Active link highlighting
  const currentPath = window.location.pathname;
  document.querySelectorAll(".navbar-links a").forEach((link) => {
    if (link.getAttribute("href") === currentPath) {
      link.classList.add("active");
    }
  });
}

// =============================================
// ANIMATIONS & INTERACTIONS
// =============================================
function initializeAnimations() {
  // Intersection Observer for scroll animations
  const observerOptions = {
    root: null,
    rootMargin: "0px",
    threshold: 0.1,
  };

  const observer = new IntersectionObserver(function (entries) {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("animated");
      }
    });
  }, observerOptions);

  // Observe elements for animation
  document
    .querySelectorAll(".feature-card, .stat-card, .section-grid")
    .forEach((el) => {
      observer.observe(el);
    });

  // Floating animation for elements
  const floatElements = document.querySelectorAll(".float-animation");
  floatElements.forEach((el) => {
    el.style.animation = "float 3s ease-in-out infinite";
  });

  // Tooltips
  initializeTooltips();
}

function initializeTooltips() {
  const tooltipElements = document.querySelectorAll("[data-tooltip]");

  tooltipElements.forEach((el) => {
    el.addEventListener("mouseenter", function (e) {
      const tooltip = document.createElement("div");
      tooltip.className = "tooltip";
      tooltip.textContent = this.getAttribute("data-tooltip");
      tooltip.style.position = "absolute";
      tooltip.style.background = "var(--bg-dark-1)";
      tooltip.style.color = "var(--text-primary)";
      tooltip.style.padding = "8px 12px";
      tooltip.style.borderRadius = "6px";
      tooltip.style.fontSize = "0.85em";
      tooltip.style.zIndex = "10000";
      tooltip.style.border = "1px solid var(--glass-border)";
      tooltip.style.maxWidth = "200px";
      tooltip.style.wordWrap = "break-word";

      document.body.appendChild(tooltip);

      const rect = this.getBoundingClientRect();
      tooltip.style.left = rect.left + "px";
      tooltip.style.top = rect.top - tooltip.offsetHeight - 10 + "px";

      this.tooltipElement = tooltip;
    });

    el.addEventListener("mouseleave", function () {
      if (this.tooltipElement) {
        this.tooltipElement.remove();
        this.tooltipElement = null;
      }
    });
  });
}

// =============================================
// SESSION MANAGEMENT
// =============================================
function initializeSession() {
  // Generate or retrieve session ID
  let sessionId = localStorage.getItem("neural_sync_session_id");

  if (!sessionId) {
    sessionId =
      "session_" + Date.now() + "_" + Math.random().toString(36).substr(2, 9);
    localStorage.setItem("neural_sync_session_id", sessionId);
  }

  // Store session analytics
  const sessionData = {
    session_id: sessionId,
    started_at: new Date().toISOString(),
    user_agent: navigator.userAgent,
    screen_resolution: window.screen.width + "x" + window.screen.height,
  };

  localStorage.setItem("session_data", JSON.stringify(sessionData));
}

// =============================================
// FORM VALIDATIONS
// =============================================
function initializeFormValidations() {
  const forms = document.querySelectorAll("form[data-validate]");

  forms.forEach((form) => {
    form.addEventListener("submit", function (e) {
      if (!validateForm(this)) {
        e.preventDefault();
        return false;
      }
    });
  });

  // Real-time validation
  document.querySelectorAll("[data-validate-input]").forEach((input) => {
    input.addEventListener("blur", function () {
      validateInput(this);
    });

    input.addEventListener("input", function () {
      clearInputError(this);
    });
  });
}

function validateForm(form) {
  let isValid = true;
  const inputs = form.querySelectorAll("[required], [data-validate-input]");

  inputs.forEach((input) => {
    if (!validateInput(input)) {
      isValid = false;
    }
  });

  return isValid;
}

function validateInput(input) {
  const value = input.value.trim();
  const type = input.type;
  const name = input.name;
  let isValid = true;
  let errorMessage = "";

  // Clear previous error
  clearInputError(input);

  // Required validation
  if (input.required && !value) {
    errorMessage = "This field is required";
    isValid = false;
  }

  // Email validation
  if (type === "email" && value) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(value)) {
      errorMessage = "Please enter a valid email address";
      isValid = false;
    }
  }

  // Length validation
  const minLength = input.getAttribute("minlength");
  const maxLength = input.getAttribute("maxlength");

  if (minLength && value.length < minLength) {
    errorMessage = `Minimum ${minLength} characters required`;
    isValid = false;
  }

  if (maxLength && value.length > maxLength) {
    errorMessage = `Maximum ${maxLength} characters allowed`;
    isValid = false;
  }

  // Show error if validation failed
  if (!isValid) {
    showInputError(input, errorMessage);
  }

  return isValid;
}

function showInputError(input, message) {
  input.classList.add("error");

  const errorDiv = document.createElement("div");
  errorDiv.className = "error-message";
  errorDiv.textContent = message;
  errorDiv.style.color = "var(--error)";
  errorDiv.style.fontSize = "0.85em";
  errorDiv.style.marginTop = "5px";

  input.parentNode.appendChild(errorDiv);
}

function clearInputError(input) {
  input.classList.remove("error");

  const errorDiv = input.parentNode.querySelector(".error-message");
  if (errorDiv) {
    errorDiv.remove();
  }
}

// =============================================
// THEME MANAGEMENT
// =============================================
function initializeTheme() {
  // Check for saved theme preference
  const savedTheme = localStorage.getItem("neural_sync_theme");

  if (savedTheme === "light") {
    setLightTheme();
  }

  // Theme toggle functionality
  const themeToggle = document.getElementById("themeToggle");
  if (themeToggle) {
    themeToggle.addEventListener("click", toggleTheme);
  }
}

function toggleTheme() {
  const currentTheme = document.body.classList.contains("light-theme")
    ? "light"
    : "dark";

  if (currentTheme === "dark") {
    setLightTheme();
  } else {
    setDarkTheme();
  }
}

function setLightTheme() {
  document.body.classList.add("light-theme");
  localStorage.setItem("neural_sync_theme", "light");

  // Update CSS variables for light theme
  document.documentElement.style.setProperty("--bg-dark-1", "#f8fafc");
  document.documentElement.style.setProperty("--bg-dark-2", "#f1f5f9");
  document.documentElement.style.setProperty("--bg-dark-3", "#e2e8f0");
  document.documentElement.style.setProperty("--text-primary", "#1e293b");
  document.documentElement.style.setProperty("--text-secondary", "#64748b");
  document.documentElement.style.setProperty(
    "--glass-bg",
    "rgba(255, 255, 255, 0.8)",
  );
  document.documentElement.style.setProperty(
    "--glass-border",
    "rgba(0, 0, 0, 0.1)",
  );
}

function setDarkTheme() {
  document.body.classList.remove("light-theme");
  localStorage.setItem("neural_sync_theme", "dark");

  // Reset to default dark theme
  document.documentElement.style.setProperty("--bg-dark-1", "#020617");
  document.documentElement.style.setProperty("--bg-dark-2", "#050B18");
  document.documentElement.style.setProperty("--bg-dark-3", "#0a0f1f");
  document.documentElement.style.setProperty("--text-primary", "#E5E7EB");
  document.documentElement.style.setProperty("--text-secondary", "#9CA3AF");
  document.documentElement.style.setProperty(
    "--glass-bg",
    "rgba(255, 255, 255, 0.08)",
  );
  document.documentElement.style.setProperty(
    "--glass-border",
    "rgba(255, 255, 255, 0.15)",
  );
}

// =============================================
// API COMMUNICATION
// =============================================
class NeuralSyncAPI {
  static async sendMessage(message) {
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error("Error sending message:", error);
      throw error;
    }
  }

  static async verifyMessage(messageId, hash) {
    try {
      const response = await fetch("/api/verify", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ id: messageId, hash }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error("Error verifying message:", error);
      throw error;
    }
  }

  static async getAnalytics() {
    try {
      const response = await fetch("/api/analytics");

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error("Error fetching analytics:", error);
      throw error;
    }
  }
}

// =============================================
// CHAT FUNCTIONALITY
// =============================================
class ChatManager {
  constructor() {
    this.messagesContainer = document.getElementById("chatMessages");
    this.inputField = document.getElementById("messageInput");
    this.sendButton = document.getElementById("sendBtn");
    this.form = document.getElementById("chatForm");

    if (this.form) {
      this.initializeChat();
    }
  }

  initializeChat() {
    // Form submission
    this.form.addEventListener("submit", (e) => {
      e.preventDefault();
      this.sendMessage();
    });

    // Enter key to send (Shift+Enter for new line)
    this.inputField.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    });

    // Input validation
    this.inputField.addEventListener("input", () => {
      this.sendButton.disabled = !this.inputField.value.trim();
    });

    // Load initial messages if any
    this.loadInitialMessages();
  }

  async sendMessage() {
    const message = this.inputField.value.trim();
    if (!message) return;

    // Add user message
    this.addMessage(message, "user");
    this.inputField.value = "";
    this.sendButton.disabled = true;

    // Show typing indicator
    this.showTypingIndicator();

    try {
      // Send to API
      const response = await NeuralSyncAPI.sendMessage(message);

      // Remove typing indicator
      this.removeTypingIndicator();

      // Add bot response
      this.addMessage(response.bot_response, "bot", response.hash);
    } catch (error) {
      this.removeTypingIndicator();
      this.addMessage(
        "Sorry, there was an error processing your message. Please try again.",
        "bot",
      );
      console.error("Chat error:", error);
    }
  }

  addMessage(content, sender, hash = null) {
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${sender}`;

    const time = new Date().toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    });

    let html = `
            <div class="message-bubble">
                ${this.escapeHtml(content)}
        `;

    if (hash && sender === "bot") {
      html += `
                <div class="hash-badge" title="SHA-256 Hash: ${hash}" onclick="copyToClipboard('${hash}')">
                    🔒 ${hash.substring(0, 16)}...
                </div>
            `;
    }

    html += `
            </div>
            <div class="message-time">${time}</div>
        `;

    messageDiv.innerHTML = html;

    // Remove empty state if present
    const emptyState = this.messagesContainer.querySelector(".chat-empty");
    if (emptyState) {
      emptyState.remove();
    }

    this.messagesContainer.appendChild(messageDiv);
    this.scrollToBottom();

    // Add animation
    messageDiv.style.animation = "slideInUp 0.3s ease-out";
  }

  showTypingIndicator() {
    const indicator = document.createElement("div");
    indicator.id = "typingIndicator";
    indicator.className = "message bot";
    indicator.innerHTML = `
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        `;

    this.messagesContainer.appendChild(indicator);
    this.scrollToBottom();
  }

  removeTypingIndicator() {
    const indicator = document.getElementById("typingIndicator");
    if (indicator) {
      indicator.remove();
    }
  }

  loadInitialMessages() {
    // Check if there are existing messages
    const existingMessages =
      this.messagesContainer.querySelectorAll(".message");

    if (existingMessages.length === 0) {
      // Add welcome message
      setTimeout(() => {
        this.addMessage(
          "Hello! I'm NeuralSync, your transparent AI assistant. Every conversation we have is cryptographically secured with SHA-256 hashing. How can I help you today?",
          "bot",
          "sha256-demo-hash-for-welcome-message",
        );
      }, 1000);
    }
  }

  scrollToBottom() {
    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
  }

  escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }
}

// =============================================
// DASHBOARD CHART FUNCTIONALITY
// =============================================
class DashboardCharts {
  constructor() {
    this.activityChart = null;
    this.initializeCharts();
  }

  initializeCharts() {
    const activityChartCanvas = document.getElementById("activityChart");
    if (activityChartCanvas) {
      this.createActivityChart();
    }

    this.loadRealTimeData();
  }

  createActivityChart() {
    const ctx = document.getElementById("activityChart").getContext("2d");

    // Create gradient
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, "rgba(0, 207, 255, 0.3)");
    gradient.addColorStop(1, "rgba(124, 124, 255, 0.1)");

    // Sample data (in production, this would come from API)
    const labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    const data = [12, 19, 8, 15, 22, 13, 18];

    this.activityChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Messages per Day",
            data: data,
            backgroundColor: gradient,
            borderColor: "#00CFFF",
            borderWidth: 3,
            fill: true,
            tension: 0.4,
            pointBackgroundColor: "#00CFFF",
            pointBorderColor: "#7C7CFF",
            pointBorderWidth: 2,
            pointRadius: 5,
            pointHoverRadius: 7,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            labels: {
              color: "#E5E7EB",
              font: {
                family: "'Space Grotesk', sans-serif",
                size: 14,
              },
            },
          },
          filler: {
            propagate: true,
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: {
              color: "rgba(255, 255, 255, 0.05)",
            },
            ticks: {
              color: "#9CA3AF",
              precision: 0,
              font: {
                family: "'Inter', sans-serif",
              },
            },
          },
          x: {
            grid: {
              color: "rgba(255, 255, 255, 0.05)",
            },
            ticks: {
              color: "#9CA3AF",
              font: {
                family: "'Inter', sans-serif",
              },
            },
          },
        },
      },
    });
  }

  async loadRealTimeData() {
    try {
      const analytics = await NeuralSyncAPI.getAnalytics();
      this.updateCharts(analytics);
    } catch (error) {
      console.error("Failed to load analytics:", error);
    }
  }

  updateCharts(analytics) {
    // Update charts with real data
    if (this.activityChart && analytics.hourly_activity) {
      // Update chart data here
      // This is where you'd update the chart with real data
    }
  }
}

// =============================================
// UTILITY FUNCTIONS
// =============================================
function copyToClipboard(text) {
  navigator.clipboard
    .writeText(text)
    .then(() => {
      showNotification("Copied to clipboard!", "success");
    })
    .catch((err) => {
      console.error("Failed to copy:", err);
      showNotification("Failed to copy", "error");
    });
}

function showNotification(message, type = "info") {
  const notification = document.createElement("div");
  notification.className = `notification notification-${type}`;
  notification.textContent = message;
  notification.style.position = "fixed";
  notification.style.top = "20px";
  notification.style.right = "20px";
  notification.style.padding = "15px 25px";
  notification.style.borderRadius = "10px";
  notification.style.background =
    type === "success"
      ? "var(--success)"
      : type === "error"
        ? "var(--error)"
        : type === "warning"
          ? "var(--warning)"
          : "var(--glass-bg)";
  notification.style.color = "white";
  notification.style.zIndex = "10000";
  notification.style.boxShadow = "0 10px 30px rgba(0, 0, 0, 0.3)";
  notification.style.animation = "fadeInUp 0.3s ease-out";

  document.body.appendChild(notification);

  setTimeout(() => {
    notification.style.animation = "fadeInUp 0.3s ease-out reverse";
    setTimeout(() => {
      notification.remove();
    }, 300);
  }, 3000);
}

function formatDate(dateString) {
  const date = new Date(dateString);
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatHash(hash, length = 16) {
  if (!hash) return "";
  return hash.length > length ? hash.substring(0, length) + "..." : hash;
}

// =============================================
// HISTORY PAGE FUNCTIONALITY
// =============================================
class HistoryManager {
  constructor() {
    this.searchInput = document.getElementById("searchInput");
    this.sortButton = document.getElementById("sortBtn");
    this.chatCards = document.getElementById("chatCards");
    this.pagination = document.getElementById("pagination");

    if (this.chatCards) {
      this.initializeHistory();
    }
  }

  initializeHistory() {
    // Search functionality
    if (this.searchInput) {
      this.searchInput.addEventListener("input", (e) => {
        this.filterConversations(e.target.value.toLowerCase());
      });
    }

    // Sort functionality
    if (this.sortButton) {
      let sortAscending = false;
      this.sortButton.addEventListener("click", () => {
        this.sortConversations(sortAscending);
        sortAscending = !sortAscending;
        this.sortButton.innerHTML = `<i class="fas fa-sort-${sortAscending ? "up" : "down"}"></i> Sort ${sortAscending ? "Newest" : "Oldest"}`;
      });
    }

    // Pagination
    if (this.pagination) {
      this.setupPagination();
    }

    // Copy hash buttons
    this.setupCopyButtons();
  }

  filterConversations(query) {
    const cards = this.chatCards.querySelectorAll(".chat-card");

    cards.forEach((card) => {
      const text = card.textContent.toLowerCase();
      if (text.includes(query)) {
        card.style.display = "";
        card.style.animation = "slideInUp 0.4s ease-out";
      } else {
        card.style.display = "none";
      }
    });
  }

  sortConversations(ascending) {
    const cards = Array.from(this.chatCards.querySelectorAll(".chat-card"));

    cards.sort((a, b) => {
      const idA = parseInt(a.getAttribute("data-id"));
      const idB = parseInt(b.getAttribute("data-id"));
      return ascending ? idA - idB : idB - idA;
    });

    cards.forEach((card, index) => {
      card.style.animation = `slideInUp 0.4s ease-out ${index * 0.05}s both`;
      this.chatCards.appendChild(card);
    });
  }

  setupPagination() {
    // This would be populated from server-side data
    // For demo, we'll create simple pagination
    const totalPages = parseInt(
      this.pagination.getAttribute("data-total-pages") || "1",
    );
    const currentPage = parseInt(
      this.pagination.getAttribute("data-current-page") || "1",
    );

    let html = "";

    // Previous button
    html += `<button onclick="historyManager.goToPage(${currentPage - 1})" ${currentPage === 1 ? "disabled" : ""}>
                    <i class="fas fa-chevron-left"></i>
                 </button>`;

    // Page numbers
    for (let i = 1; i <= totalPages; i++) {
      if (
        i === 1 ||
        i === totalPages ||
        (i >= currentPage - 1 && i <= currentPage + 1)
      ) {
        html += `<button onclick="historyManager.goToPage(${i})" ${i === currentPage ? 'class="active"' : ""}>
                            ${i}
                         </button>`;
      } else if (i === currentPage - 2 || i === currentPage + 2) {
        html += `<span>...</span>`;
      }
    }

    // Next button
    html += `<button onclick="historyManager.goToPage(${currentPage + 1})" ${currentPage === totalPages ? "disabled" : ""}>
                    <i class="fas fa-chevron-right"></i>
                 </button>`;

    this.pagination.innerHTML = html;
  }

  goToPage(page) {
    window.location.href = `/history?page=${page}`;
  }

  setupCopyButtons() {
    document.addEventListener("click", (e) => {
      if (
        e.target.classList.contains("copy-btn") ||
        e.target.closest(".copy-btn")
      ) {
        const button = e.target.classList.contains("copy-btn")
          ? e.target
          : e.target.closest(".copy-btn");
        const hash = button.getAttribute("data-hash");

        if (hash) {
          copyToClipboard(hash);

          // Visual feedback
          const originalText = button.innerHTML;
          button.innerHTML = '<i class="fas fa-check"></i> Copied!';
          button.classList.add("copied");

          setTimeout(() => {
            button.innerHTML = originalText;
            button.classList.remove("copied");
          }, 2000);
        }
      }
    });
  }
}

// =============================================
// LAZY LOADING FOR IMAGES/GIFS
// =============================================
function initializeLazyLoading() {
  const lazyImages = document.querySelectorAll("img[data-src]");

  const imageObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const img = entry.target;
        img.src = img.getAttribute("data-src");
        img.removeAttribute("data-src");
        imageObserver.unobserve(img);
      }
    });
  });

  lazyImages.forEach((img) => imageObserver.observe(img));
}

// =============================================
// INITIALIZE COMPONENTS
// =============================================
// Initialize Chat Manager
let chatManager = null;
if (document.getElementById("chatForm")) {
  chatManager = new ChatManager();
}

// Initialize Dashboard Charts
let dashboardCharts = null;
if (document.getElementById("activityChart")) {
  dashboardCharts = new DashboardCharts();
}

// Initialize History Manager
let historyManager = null;
if (document.getElementById("chatCards")) {
  historyManager = new HistoryManager();
}

// Initialize lazy loading
initializeLazyLoading();

// =============================================
// GLOBAL EXPORTS (for use in templates)
// =============================================
window.NeuralSyncAPI = NeuralSyncAPI;
window.copyToClipboard = copyToClipboard;
window.formatDate = formatDate;
window.formatHash = formatHash;

// Make managers globally available for debugging
if (chatManager) window.chatManager = chatManager;
if (dashboardCharts) window.dashboardCharts = dashboardCharts;
if (historyManager) window.historyManager = historyManager;
