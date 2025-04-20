// detailPageScript.js
window.onload = function() {
    const applicationId = new URL(window.location.href).pathname.split('/').pop();
    fetch(`/get-courses/${applicationId}`)
        .then(res => res.json())
        .then(courses => {
            document.getElementById('studentName').innerText = `Courses for Application ID: ${applicationId}`;
            const courseListDiv = document.getElementById('courseList');
            courses.forEach(course => {
                const courseInfo = document.createElement('div');
                courseInfo.innerHTML = `<p>${course.course_name} - Credits: ${course.credits}, Grade: ${course.grade}</p>`;
                courseListDiv.appendChild(courseInfo);
            });
        })
        .catch(err => {
            console.error("Error fetching course details:", err);
            alert("Unable to load course details.");
        });
};
