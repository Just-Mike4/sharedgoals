from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Group, GroupMember, Expense, ExpenseShare, Repayment


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']


class GroupMemberSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='user.username')
    
    class Meta:
        model = GroupMember
        fields = ['username', 'role']


class ExpenseShareSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='user.username')
    
    class Meta:
        model = ExpenseShare
        fields = ['username', 'share']


class ExpenseShareCreateSerializer(serializers.Serializer):
    username = serializers.CharField()
    share = serializers.DecimalField(max_digits=5, decimal_places=2)


class ExpenseSerializer(serializers.ModelSerializer):
    paid_by = serializers.SlugRelatedField(
        slug_field='username',
        queryset=User.objects.all()
    )
    shares = ExpenseShareSerializer(source='expenseshare_set', many=True, read_only=True)
    shared_between = ExpenseShareCreateSerializer(many=True, write_only=True)
    
    class Meta:
        model = Expense
        fields = ['id', 'title', 'amount', 'date', 'description', 'paid_by', 'shares', 'shared_between']
    
    def create(self, validated_data):
        shared_between_data = validated_data.pop('shared_between')
        group = validated_data['group']
        expense = Expense.objects.create(**validated_data)
        
        # Create expense shares
        for share_data in shared_between_data:
            username = share_data['username']
            try:
                user = User.objects.get(username=username)
                # Check if user is member of the group
                if GroupMember.objects.filter(group=group, user=user).exists():
                    ExpenseShare.objects.create(
                        expense=expense,
                        user=user,
                        share=share_data['share']
                    )
            except User.DoesNotExist:
                pass  # Skip if user doesn't exist
        
        return expense


class GroupSerializer(serializers.ModelSerializer):
    created_by = serializers.ReadOnlyField(source='created_by.username')
    members = GroupMemberSerializer(source='groupmember_set', many=True, read_only=True)
    
    class Meta:
        model = Group
        fields = ['id', 'name', 'created_by', 'members']


class GroupDetailSerializer(GroupSerializer):
    recent_expenses = serializers.SerializerMethodField()
    
    class Meta(GroupSerializer.Meta):
        fields = GroupSerializer.Meta.fields + ['recent_expenses']
    
    def get_recent_expenses(self, obj):
        # Get 5 most recent expenses
        expenses = Expense.objects.filter(group=obj).order_by('-date')[:5]
        return ExpenseSerializer(expenses, many=True).data


class RepaymentSerializer(serializers.ModelSerializer):
    from_user = serializers.SlugRelatedField(
        slug_field='username',
        queryset=User.objects.all()
    )

    to_user = serializers.SlugRelatedField(
        slug_field='username',
        queryset=User.objects.all()
    )
    
    class Meta:
        model = Repayment
        fields = ['id', 'from_user', 'to_user', 'amount', 'date']
    
    def validate(self, data):
        # Ensure both users are in the group
        group = self.context['group']
        if not GroupMember.objects.filter(group=group, user=data['from_user']).exists():
            raise serializers.ValidationError(f"User {data['from_user'].username} is not a member of this group")
        if not GroupMember.objects.filter(group=group, user=data['to_user']).exists():
            raise serializers.ValidationError(f"User {data['to_user'].username} is not a member of this group")
        return data


class BalanceSerializer(serializers.Serializer):
    username = serializers.CharField()
    balance = serializers.DecimalField(max_digits=10, decimal_places=2)


class SummaryItemSerializer(serializers.Serializer):
    from_user = serializers.CharField(source='from')
    to_user = serializers.CharField(source='to')
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)