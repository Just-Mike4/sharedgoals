from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.models import User
from django.db.models import Sum, F, Q
from django.shortcuts import get_object_or_404

from .models import Group, GroupMember, Expense, ExpenseShare, Repayment
from .serializers import (
    GroupSerializer,
    GroupDetailSerializer,
    ExpenseSerializer,
    RepaymentSerializer,
    BalanceSerializer,
    SummaryItemSerializer
)


class IsGroupMember(permissions.BasePermission):
    """
    Custom permission to only allow members of a group to access it.
    """
    def has_permission(self, request, view):
        group_id = view.kwargs.get('group_id')
        if not group_id:
            return True
        
        return GroupMember.objects.filter(
            group_id=group_id,
            user=request.user
        ).exists()


class IsGroupAdmin(permissions.BasePermission):
    """
    Custom permission to only allow admins of a group to perform certain actions.
    """
    def has_permission(self, request, view):
        group_id = view.kwargs.get('group_id')
        if not group_id:
            return True
        
        return GroupMember.objects.filter(
            group_id=group_id,
            user=request.user,
            role='admin'
        ).exists()


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return GroupDetailSerializer
        return GroupSerializer
    
    def get_queryset(self):
        # Only show groups the user is a member of
        return Group.objects.filter(groupmember__user=self.request.user)
    
    def perform_create(self, serializer):
        # Add the creator as admin member
        group = serializer.save(created_by=self.request.user)
        GroupMember.objects.create(
            group=group,
            user=self.request.user,
            role='admin'
        )
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsGroupAdmin])
    def invite(self, request, pk=None):
        group = self.get_object()
        username = request.data.get('username')
        
        try:
            user = User.objects.get(username=username)
            
            # Check if already member
            if GroupMember.objects.filter(group=group, user=user).exists():
                return Response(
                    {'detail': 'User is already a member of this group'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Add user to group
            GroupMember.objects.create(
                group=group,
                user=user,
                role='member'
            )
            
            return Response({'detail': f'User {username} added to the group'})
            
        except User.DoesNotExist:
            return Response(
                {'detail': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class GroupExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated, IsGroupMember]
    
    def get_queryset(self):
        group_id = self.kwargs['group_id']
        queryset = Expense.objects.filter(group_id=group_id)
        
        # Optional filtering
        username = self.request.query_params.get('username')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if username:
            queryset = queryset.filter(Q(paid_by__username=username) | Q(expenseshare__user__username=username))
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        return queryset.distinct()
    
    def perform_create(self, serializer):
        group_id = self.kwargs['group_id']
        group = get_object_or_404(Group, id=group_id)
        serializer.save(group=group)


class GroupRepaymentViewSet(viewsets.ModelViewSet):
    serializer_class = RepaymentSerializer
    permission_classes = [permissions.IsAuthenticated, IsGroupMember]
    
    def get_queryset(self):
        group_id = self.kwargs['group_id']
        return Repayment.objects.filter(group_id=group_id)
    
    def perform_create(self, serializer):
        group_id = self.kwargs['group_id']
        group = get_object_or_404(Group, id=group_id)
        serializer.save(group=group)
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        group_id = self.kwargs['group_id']
        context['group'] = get_object_or_404(Group, id=group_id)
        return context


class GroupSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsGroupMember]
    
    def get(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        
        # Calculate what each user owes
        members = GroupMember.objects.filter(group=group)
        summary = []
        
        # First, calculate raw expense balances
        for member in members:
            user = member.user
            
            # Money spent by this user
            spent = Expense.objects.filter(
                group=group,
                paid_by=user
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Money this user owes for expenses
            user_shares = ExpenseShare.objects.filter(
                expense__group=group,
                user=user
            ).select_related('expense')
            
            owes = 0
            for share in user_shares:
                share_percentage = share.share
                expense_amount = share.expense.amount
                owes += (share_percentage / 100) * expense_amount
            
            # Money this user has paid back
            paid_back = Repayment.objects.filter(
                group=group,
                from_user=user
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Money this user has received as repayment
            received = Repayment.objects.filter(
                group=group,
                to_user=user
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Calculate net balance
            balance = spent - owes + paid_back - received
            
            summary.append({
                'username': user.username,
                'spent': spent,
                'owes': owes,
                'paid_back': paid_back,
                'received': received,
                'balance': balance
            })
        
        # Now generate who owes whom
        debts = []
        creditors = sorted([m for m in summary if m['balance'] > 0], key=lambda x: x['balance'], reverse=True)
        debtors = sorted([m for m in summary if m['balance'] < 0], key=lambda x: x['balance'])
        
        for debtor in debtors:
            debt_amount = abs(debtor['balance'])
            for creditor in creditors:
                if debt_amount <= 0 or creditor['balance'] <= 0:
                    continue
                
                amount_to_pay = min(debt_amount, creditor['balance'])
                
                if amount_to_pay > 0:
                    debts.append({
                        'from': debtor['username'],
                        'to': creditor['username'],
                        'amount': amount_to_pay
                    })
                    
                    creditor['balance'] -= amount_to_pay
                    debt_amount -= amount_to_pay
        
        return Response({'summary': SummaryItemSerializer(debts, many=True).data})


class GroupBalancesView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsGroupMember]
    
    def get(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        
        # Calculate balances for each member
        members = GroupMember.objects.filter(group=group)
        balances = []
        
        for member in members:
            user = member.user
            
            # Money spent by this user
            spent = Expense.objects.filter(
                group=group,
                paid_by=user
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Money this user owes for expenses
            user_shares = ExpenseShare.objects.filter(
                expense__group=group,
                user=user
            ).select_related('expense')
            
            owes = 0
            for share in user_shares:
                share_percentage = share.share
                expense_amount = share.expense.amount
                owes += (share_percentage / 100) * expense_amount
            
            # Money this user has paid back
            paid_back = Repayment.objects.filter(
                group=group,
                from_user=user
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Money this user has received as repayment
            received = Repayment.objects.filter(
                group=group,
                to_user=user
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Calculate net balance
            balance = spent - owes + paid_back - received
            
            balances.append({
                'username': user.username,
                'balance': balance
            })
        
        return Response(BalanceSerializer(balances, many=True).data)