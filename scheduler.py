from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from models import db, TaskSchedule, ActivityLog
import pytz

class TaskScheduler:
    def __init__(self, app):
        self.app = app
        self.scheduler = BackgroundScheduler(timezone=pytz.UTC)
        self.scheduler.start()
        print("TaskScheduler initialized and started")
        self.load_schedules()

    def load_schedules(self):
        """Load all enabled schedules from the database"""
        with self.app.app_context():
            schedules = TaskSchedule.query.filter_by(enabled=True).all()
            print(f"Loading {len(schedules)} enabled schedules")
            for schedule in schedules:
                self.add_job(schedule)

    def add_job(self, schedule):
        """Add a job to the scheduler based on the schedule configuration"""
        if not schedule.enabled:
            print(f"Schedule {schedule.name} is disabled, skipping")
            return

        job_id = f"{schedule.action}_{schedule.id}"
        print(f"Adding job {job_id} with cron: {schedule.cron}")
        
        # Remove existing job if it exists
        try:
            if self.scheduler.get_job(job_id):
                print(f"Removing existing job {job_id}")
                self.scheduler.remove_job(job_id)
        except Exception as e:
            print(f"Error removing existing job: {str(e)}")

        # Create trigger from cron expression
        try:
            trigger = CronTrigger.from_crontab(schedule.cron)
            print(f"Created trigger for {job_id}: {trigger}")
        except Exception as e:
            print(f"Error creating trigger for {job_id}: {str(e)}")
            return

        try:
            # Store schedule info that we need in the job
            schedule_info = {
                'id': schedule.id,
                'name': schedule.name,
                'action': schedule.action
            }

            def job_func(schedule_info=schedule_info):
                print(f"Executing scheduled job {job_id}")
                with self.app.app_context():
                    try:
                        # Log the start of the scheduled task
                        log = ActivityLog(
                            message=f"Running scheduled task: {schedule_info['name']}",
                            type='info',
                            timestamp=datetime.utcnow()
                        )
                        db.session.add(log)
                        db.session.commit()
                        print(f"Added start log for {job_id}")

                        # Update last_run timestamp
                        schedule = TaskSchedule.query.get(schedule_info['id'])
                        if schedule:
                            schedule.last_run = datetime.utcnow()
                            db.session.commit()
                            print(f"Updated last_run for {job_id}")

                        # Execute the task based on action
                        if schedule_info['action'] == 'remount_downloads':
                            from app import run_selenium_command
                            run_selenium_command('remount_downloads')
                        elif schedule_info['action'] == 'reboot_repair':
                            from app import run_selenium_command
                            run_selenium_command('reboot_repair')
                        elif schedule_info['action'] == 'reboot_refresh':
                            from app import run_selenium_command
                            run_selenium_command('reboot_refresh')
                        elif schedule_info['action'] == 'reboot_worker':
                            from app import run_selenium_command
                            run_selenium_command('reboot_worker')
                        elif schedule_info['action'] == 'jellyfin_scan':
                            from app import jellyfin_scan_library
                            result, status_code = jellyfin_scan_library()
                            if not result['success']:
                                print(f"Jellyfin scan failed: {result.get('error', 'Unknown error')}")
                                raise Exception(result.get('error', 'Jellyfin scan failed'))
                        else:
                            raise ValueError(f"Unknown action: {schedule_info['action']}")
                        print(f"Executed action {schedule_info['action']} for {job_id}")

                        # Log successful completion
                        log = ActivityLog(
                            message=f"Completed scheduled task: {schedule_info['name']}",
                            type='success',
                            timestamp=datetime.utcnow()
                        )
                        db.session.add(log)
                        db.session.commit()
                        print(f"Added completion log for {job_id}")
                    except Exception as e:
                        error_msg = str(e)
                        print(f"Error executing job {job_id}: {error_msg}")
                        # Log any errors
                        log = ActivityLog(
                            message=f"Failed scheduled task {schedule_info['name']}: {error_msg}",
                            type='error',
                            timestamp=datetime.utcnow()
                        )
                        db.session.add(log)
                        db.session.commit()

            self.scheduler.add_job(
                job_func,
                trigger=trigger,
                id=job_id,
                replace_existing=True
            )
            print(f"Successfully added job {job_id} to scheduler")
            # Print next run time
            job = self.scheduler.get_job(job_id)
            if job:
                print(f"Next run time for {job_id}: {job.next_run_time}")
        except Exception as e:
            print(f"Error adding job to scheduler: {str(e)}")

    def update_schedule(self, schedule):
        """Update an existing schedule"""
        print(f"Updating schedule {schedule.name}")
        self.add_job(schedule)

    def remove_schedule(self, schedule):
        """Remove a schedule from the scheduler"""
        job_id = f"{schedule.action}_{schedule.id}"
        print(f"Removing schedule {job_id}")
        try:
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                print(f"Successfully removed job {job_id}")
        except Exception as e:
            print(f"Error removing schedule: {str(e)}")

    def shutdown(self):
        """Shutdown the scheduler"""
        print("Shutting down scheduler")
        self.scheduler.shutdown()

    def reload_schedules(self):
        """Reload all enabled schedules from the database"""
        print("Reloading all schedules from the database")
        
        # First, clear all existing jobs from the scheduler
        self.scheduler.remove_all_jobs()
        print("Removed all existing jobs from scheduler")
        
        # Load all enabled schedules
        with self.app.app_context():
            schedules = TaskSchedule.query.filter_by(enabled=True).all()
            print(f"Loading {len(schedules)} enabled schedules")
            
            for schedule in schedules:
                self.add_job(schedule)
                
        print("Finished reloading schedules") 