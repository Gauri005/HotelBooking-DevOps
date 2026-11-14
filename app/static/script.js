const roomTypes = ["Standard", "Deluxe", "Suite"];
const availabilityForm = document.querySelector("#availability-form");
const availabilityMessage = document.querySelector("#availability-message");
const bookingForm = document.querySelector("#booking-form");
const bookingMessage = document.querySelector("#booking-message");
const bookingSubmit = document.querySelector("#booking-submit");
const confirmation = document.querySelector("#confirmation");
const menuToggle = document.querySelector(".menu-toggle");
const navLinks = document.querySelector(".nav-links");

function formatRoomType(roomType) {
  return `${roomType} Room`;
}

function formatDate(value) {
  return new Date(`${value}T00:00:00`).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric"
  });
}

function setMessage(element, message, type = "") {
  element.textContent = message;
  element.className = `form-message ${type}`.trim();
}

function validateDates(checkIn, checkOut) {
  if (!checkIn || !checkOut) {
    return "Please choose both check-in and check-out dates.";
  }
  if (checkOut <= checkIn) {
    return "Check-out must be after check-in.";
  }
  return "";
}

async function getApiError(response) {
  try {
    const body = await response.json();
    return body.detail || "Something went wrong. Please try again.";
  } catch {
    return "The service is unavailable right now. Please try again.";
  }
}

function setRoomStatus(roomType, available, count) {
  const status = document.querySelector(`[data-status-for="${roomType}"]`);
  status.textContent = available ? `${count} room${count === 1 ? "" : "s"} available` : "Unavailable for these dates";
  status.classList.toggle("available", available);
  status.classList.toggle("unavailable", !available);
}

async function checkAvailability(checkIn, checkOut, roomType) {
  const params = new URLSearchParams({ check_in: checkIn, check_out: checkOut, room_type: roomType });
  const response = await fetch(`/availability?${params}`);
  if (!response.ok) {
    throw new Error(await getApiError(response));
  }
  return response.json();
}

async function updateRoomStatuses(checkIn, checkOut, selectedRoomType) {
  const types = selectedRoomType ? [selectedRoomType] : roomTypes;
  const results = await Promise.all(types.map(async (roomType) => ({
    roomType,
    result: await checkAvailability(checkIn, checkOut, roomType)
  })));
  results.forEach(({ roomType, result }) => setRoomStatus(roomType, result.available, result.available_rooms));
  return results;
}

availabilityForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(availabilityForm);
  const checkIn = formData.get("check_in");
  const checkOut = formData.get("check_out");
  const roomType = formData.get("room_type");
  const dateError = validateDates(checkIn, checkOut);
  if (dateError) {
    setMessage(availabilityMessage, dateError, "error");
    return;
  }

  const button = availabilityForm.querySelector("button");
  button.disabled = true;
  setMessage(availabilityMessage, "Checking our rooms...");
  try {
    const results = await updateRoomStatuses(checkIn, checkOut, roomType);
    const result = results[0].result;
    setMessage(
      availabilityMessage,
      result.available
        ? `${formatRoomType(roomType)} is available for your dates.`
        : `There are no ${formatRoomType(roomType).toLowerCase()}s available for your dates.`,
      result.available ? "success" : "error"
    );
    document.querySelector("#booking-room-type").value = roomType;
    document.querySelector("#booking-check-in").value = checkIn;
    document.querySelector("#booking-check-out").value = checkOut;
  } catch (error) {
    setMessage(availabilityMessage, error.message, "error");
  } finally {
    button.disabled = false;
  }
});

document.querySelectorAll(".book-room").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelector("#booking-room-type").value = button.dataset.room;
    document.querySelector("#booking").scrollIntoView({ behavior: "smooth" });
    document.querySelector("#customer-name").focus({ preventScroll: true });
  });
});

bookingForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(bookingForm);
  const values = Object.fromEntries(formData.entries());
  const dateError = validateDates(values.check_in, values.check_out);
  if (dateError) {
    setMessage(bookingMessage, dateError, "error");
    return;
  }

  bookingSubmit.disabled = true;
  bookingSubmit.classList.add("is-loading");
  setMessage(bookingMessage, "Securing your room...");
  try {
    const response = await fetch("/reservations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(values)
    });
    if (!response.ok) {
      throw new Error(await getApiError(response));
    }
    const reservation = await response.json();
    document.querySelector("#confirmation-reference").textContent = `Booking reference: ${reservation.booking_reference}`;
    document.querySelector("#confirmation-name").textContent = reservation.customer_name;
    document.querySelector("#confirmation-room").textContent = formatRoomType(reservation.room_type);
    document.querySelector("#confirmation-dates").textContent = `${formatDate(reservation.check_in)} - ${formatDate(reservation.check_out)}`;
    bookingForm.hidden = true;
    bookingMessage.hidden = true;
    confirmation.hidden = false;
  } catch (error) {
    setMessage(bookingMessage, error.message, "error");
  } finally {
    bookingSubmit.disabled = false;
    bookingSubmit.classList.remove("is-loading");
  }
});

document.querySelector("#new-booking").addEventListener("click", () => {
  bookingForm.reset();
  bookingForm.hidden = false;
  bookingMessage.hidden = false;
  setMessage(bookingMessage, "");
  confirmation.hidden = true;
});

menuToggle.addEventListener("click", () => {
  const isOpen = navLinks.classList.toggle("open");
  menuToggle.setAttribute("aria-expanded", String(isOpen));
});

navLinks.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", () => {
    navLinks.classList.remove("open");
    menuToggle.setAttribute("aria-expanded", "false");
  });
});
